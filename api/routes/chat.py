"""
Chat router — Core conversational endpoint with three-way intent routing.

Handles chat session CRUD and message processing. Each incoming message
is classified by intent (department_query, calendar_query, general_query)
and routed to the appropriate processing pipeline.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from pydantic import BaseModel

from core.database import get_supabase_client
from core.prompts import (
    CALENDAR_SYSTEM_PROMPT,
    DEPARTMENT_RAG_SYSTEM_PROMPT,
    GENERAL_QUERY_SYSTEM_PROMPT,
    INTENT_CLASSIFICATION_PROMPT,
    MEMORY_SYNTHESIS_PROMPT,
    TITLE_GENERATION_PROMPT,
)
from core.rooms import get_rooms_manifest_text
from services.calendar import format_availability_for_llm, query_freebusy
from services.llm.local import get_local_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


# ── Request / Response Models ───────────────────────────────────────────────


class SendMessageRequest(BaseModel):
    session_id: str
    message: str


class CreateSessionRequest(BaseModel):
    title: str = "New Chat"


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    interactive_type: str | None = None
    interactive_payload: dict[str, Any] | None = None
    created_at: str


class SessionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    is_pinned: bool = False
    created_at: str
    updated_at: str


class UpdateSessionRequest(BaseModel):
    title: str | None = None
    is_pinned: bool | None = None


class ChatResponse(BaseModel):
    assistant_message: MessageResponse
    intent: str
    confidence: float
    session_title: str | None = None


# ── Auth Helper ─────────────────────────────────────────────────────────────


def _extract_user_id(authorization: str) -> str:
    """Extract and validate user ID from the Supabase JWT.

    The frontend sends the access token; we verify it via Supabase admin client.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header.")

    token = authorization.removeprefix("Bearer ").strip()
    db = get_supabase_client()

    try:
        user_response = db.auth.get_user(token)
        return user_response.user.id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")


# ── Session Endpoints ───────────────────────────────────────────────────────


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(authorization: str = Header(...)):
    """List all chat sessions for the authenticated user, newest first."""
    user_id = _extract_user_id(authorization)
    db = get_supabase_client()

    result = (
        db.table("chat_sessions")
        .select("*")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return result.data


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    body: CreateSessionRequest,
    authorization: str = Header(...),
):
    """Create a new chat session."""
    user_id = _extract_user_id(authorization)
    db = get_supabase_client()

    result = (
        db.table("chat_sessions")
        .insert({"user_id": user_id, "title": body.title})
        .execute()
    )
    return result.data[0]


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_session_messages(
    session_id: str,
    authorization: str = Header(...),
):
    """Retrieve all messages in a chat session, ordered chronologically."""
    user_id = _extract_user_id(authorization)
    db = get_supabase_client()

    # Verify session ownership
    session = (
        db.table("chat_sessions")
        .select("user_id")
        .eq("id", session_id)
        .single()
        .execute()
    )
    if not session.data or session.data["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Session not found.")

    result = (
        db.table("messages")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    authorization: str = Header(...),
):
    """Delete a chat session and all its messages (cascading)."""
    user_id = _extract_user_id(authorization)
    db = get_supabase_client()

    session = (
        db.table("chat_sessions")
        .select("user_id")
        .eq("id", session_id)
        .single()
        .execute()
    )
    if not session.data or session.data["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Session not found.")

    db.table("chat_sessions").delete().eq("id", session_id).execute()
    return {"status": "deleted"}


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    body: UpdateSessionRequest,
    authorization: str = Header(...),
):
    """Update a chat session (e.g., rename title, toggle pinned)."""
    user_id = _extract_user_id(authorization)
    db = get_supabase_client()

    session = (
        db.table("chat_sessions")
        .select("user_id")
        .eq("id", session_id)
        .single()
        .execute()
    )
    if not session.data or session.data["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Session not found.")

    updates = {}
    if body.title is not None:
        updates["title"] = body.title
    if body.is_pinned is not None:
        updates["is_pinned"] = body.is_pinned
        
    if not updates:
        # Nothing to update, return the existing
        return db.table("chat_sessions").select("*").eq("id", session_id).single().execute().data

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = (
        db.table("chat_sessions")
        .update(updates)
        .eq("id", session_id)
        .execute()
    )
    return result.data[0]


# ── Core Chat Endpoint ──────────────────────────────────────────────────────


async def _finalize_chat_response(
    user_id: str,
    session_id: str,
    session_title: str,
    user_message: str,
    assistant_content: str,
    interactive_type: str | None,
    interactive_payload: dict[str, Any] | None,
):
    """Background task to store messages, update timestamp, and generate session title."""
    db = get_supabase_client()
    llm = get_local_client()

    try:
        # ── Store user message ──────────────────────────────────────────────────
        await asyncio.to_thread(lambda: db.table("messages").insert({
            "session_id": session_id,
            "role": "user",
            "content": user_message,
        }).execute())

        # ── Store assistant message ─────────────────────────────────────────────
        assistant_msg_data: dict[str, Any] = {
            "session_id": session_id,
            "role": "assistant",
            "content": assistant_content,
        }
        if interactive_type:
            assistant_msg_data["interactive_type"] = interactive_type
            assistant_msg_data["interactive_payload"] = interactive_payload

        await asyncio.to_thread(lambda: db.table("messages").insert(assistant_msg_data).execute())

        # ── Auto-generate session title from first message ──────────────────────
        generated_title = None
        if session_title == "New Chat" or session_title == "New Chat Session":
            title_prompt = TITLE_GENERATION_PROMPT.format(
                user_message=user_message,
                assistant_response=assistant_content
            )
            try:
                # Use OpenRouter via hybrid client for title generation
                title_data_str = await llm.generate_title(title_prompt)
                
                # Title might be returned directly or wrapped in json. We'll strip quotes if needed.
                # If they used JSON format in previous implementation, we should safely parse it.
                title = title_data_str.strip(' \n\r\t\"\'')
                
                # Handle potential markdown json blocks
                import re
                json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", title)
                if json_match:
                    title = json_match.group(1).strip()

                if title.startswith("{") and "title" in title.lower():
                    try:
                        title = json.loads(title).get("title", title)
                    except json.JSONDecodeError:
                        pass
                        
                if len(title) > 40:
                    title = title[:37] + "..."
            except Exception as e:
                logger.error("Error generating title: %s", e)
                # Fallback to simple truncation
                title = user_message.strip()
                if len(title) > 40:
                    title = title[:37] + "..."
            
            if not title:
                title = "New Chat Session"
                
            await asyncio.to_thread(lambda: db.table("chat_sessions").update({"title": title}).eq(
                "id", session_id
            ).execute())
            generated_title = title

        # ── Update session timestamp ────────────────────────────────────────────
        await asyncio.to_thread(lambda: db.table("chat_sessions").update(
            {"updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", session_id).execute())

        # ── Trigger Memory Synthesis ────────────────────────────────────────────
        # Run asynchronously so it doesn't block the finalizing step or any potential teardown
        asyncio.create_task(_synthesize_memory_task(session_id, user_id))

    except Exception:
        logger.error("Error in chat background task", exc_info=True)


@router.post("/send")
async def send_message(
    body: SendMessageRequest,
    background_tasks: BackgroundTasks,
    authorization: str = Header(...),
):
    """Process a user message through the intent routing pipeline.

    1. Run initial DB fetches and intent classification in parallel.
    2. Route to department_query (RAG), calendar_query, or general_query.
    3. Offload DB inserts and title generation to background tasks.
    4. Return the assistant response immediately.
    """
    user_id = _extract_user_id(authorization)
    db = get_supabase_client()
    llm = get_local_client()

    # ── Parallel execution of initial I/O ───────────────────────────────────
    def _fetch_db_data():
        for attempt in range(2):
            try:
                s = db.table("chat_sessions").select("*").eq("id", body.session_id).single().execute()
                if not s.data or s.data["user_id"] != user_id:
                    return s, None, None
                p = db.table("profiles").select("full_name, academic_role, department, year, interests, synthesized_memory").eq("id", user_id).single().execute()
                h = db.table("messages").select("role, content").eq("session_id", body.session_id).order("created_at", desc=True).limit(20).execute()
                if h.data:
                    h.data = h.data[::-1]
                return s, p, h
            except Exception as ex:
                if attempt == 1:
                    raise ex
                logger.warning("Supabase DB fetch attempt %d failed (%s). Retrying...", attempt + 1, ex)

    intent_prompt = INTENT_CLASSIFICATION_PROMPT.format(user_message=body.message)
    intent_task = asyncio.create_task(llm.generate_json(intent_prompt, fast_model=True))
    db_task = asyncio.to_thread(_fetch_db_data)

    try:
        db_results, intent_result = await asyncio.gather(db_task, intent_task)
        session, profile, history = db_results
    except Exception as e:
        logger.error("Error during parallel API fetches", exc_info=True)
        if "429" in str(e) or "quota" in str(e).lower():
            raise HTTPException(status_code=429, detail="LLM Rate limit exceeded. Please try again later.")
        raise HTTPException(status_code=500, detail=str(e))

    # ── Verify session ownership ────────────────────────────────────────────
    if not session.data or session.data["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Session not found.")

    profile_data = profile.data or {}
    memory_parts = []
    
    if profile_data.get("full_name"):
        memory_parts.append(f"- Name: {profile_data['full_name']}")
    if profile_data.get("academic_role"):
        memory_parts.append(f"- Role: {profile_data['academic_role']}")
    if profile_data.get("department"):
        memory_parts.append(f"- Department: {profile_data['department']}")
    if profile_data.get("year"):
        memory_parts.append(f"- Year: {profile_data['year']}")
    if profile_data.get("interests"):
        memory_parts.append(f"- Interests: {', '.join(profile_data['interests'])}")
    if profile_data.get("synthesized_memory"):
        memory_parts.append(f"- Long-term Memory: {profile_data['synthesized_memory']}")

    memory_context = ""
    if memory_parts:
        memory_context = "USER CONTEXT (Personalization Data):\n" + "\n".join(memory_parts)

    conversation_context = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in history.data
    )

    # ── Intent Classification ───────────────────────────────────────────────
    intent = intent_result.get("intent", "general_query")
    confidence = float(intent_result.get("confidence", 0.5))

    # Fallback for unrecognized intents
    if intent not in ("department_query", "calendar_query", "general_query"):
        logger.warning("Unrecognized intent '%s', falling back to general_query", intent)
        intent = "general_query"

    from fastapi.responses import StreamingResponse

    async def event_generator():
        # Setup metadata
        tmp_id = f"tmp-{int(datetime.now().timestamp())}"
        
        try:
            if intent == "calendar_query":
                # Do not stream calendar queries since we need to extract structured JSON
                assistant_content, interactive_type, interactive_payload = (
                    await _handle_calendar_query(
                        llm, body.message, conversation_context, memory_context
                    )
                )
                
                # Yield metadata with payload
                meta = {
                    "type": "metadata",
                    "intent": intent,
                    "confidence": confidence,
                    "interactive_type": interactive_type,
                    "interactive_payload": interactive_payload,
                    "message_id": tmp_id
                }
                yield f"data: {json.dumps(meta)}\n\n"
                
                # Yield the full text chunk
                yield f"data: {json.dumps({'type': 'chunk', 'text': assistant_content})}\n\n"
                
                full_content = assistant_content
                
            else:
                # For department and general queries, stream the response!
                interactive_type = None
                interactive_payload = None
                
                meta = {
                    "type": "metadata",
                    "intent": intent,
                    "confidence": confidence,
                    "interactive_type": None,
                    "interactive_payload": None,
                    "message_id": tmp_id
                }
                yield f"data: {json.dumps(meta)}\n\n"
                
                full_content = ""
                if intent == "department_query":
                    stream = _handle_department_query_stream(
                        llm, body.message, conversation_context, memory_context,
                        search_keywords=intent_result.get("keywords")
                    )
                else:
                    stream = _handle_general_query_stream(
                        llm, body.message, conversation_context, memory_context
                    )
                    
                async for chunk in stream:
                    yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"
                    full_content += chunk
            
            # Now that the stream is finished, we must finalize the DB inserts.
            # We await this directly since we are inside the streaming generator.
            await _finalize_chat_response(
                user_id=user_id,
                session_id=body.session_id,
                session_title=session.data.get("title", "New Chat"),
                user_message=body.message,
                assistant_content=full_content,
                interactive_type=interactive_type,
                interactive_payload=interactive_payload
            )
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except (asyncio.CancelledError, GeneratorExit):
            logger.info("SSE stream cancelled by client connection drop.")
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "ResourceExhausted" in err_msg or "quota" in err_msg.lower():
                clean_msg = "Rate limit reached. Please wait a moment and try again!"
                logger.warning("LLM Quota Exceeded during stream.")
                yield f"data: {json.dumps({'type': 'error', 'detail': clean_msg})}\n\n"
            else:
                logger.error("Error during streaming generation", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'detail': err_msg})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Memory Synthesis Endpoint ───────────────────────────────────────────────


@router.post("/sessions/{session_id}/synthesize")
async def _synthesize_memory_task(session_id: str, user_id: str):
    """Background task to synthesize memory using the local LLM client."""
    db = get_supabase_client()
    llm = get_local_client()

    try:
        # Load conversation
        messages = (
            db.table("messages")
            .select("role, content")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )
        if not messages.data:
            return {"status": "no_messages"}

        conversation = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in messages.data
        )

        # Load existing memory
        profile = (
            db.table("profiles")
            .select("synthesized_memory")
            .eq("id", user_id)
            .single()
            .execute()
        )
        existing_memory = (profile.data or {}).get("synthesized_memory", "")

        # Synthesize new memory using the Hybrid LLM (Groq -> OpenRouter -> Gemini)
        synthesis_prompt = MEMORY_SYNTHESIS_PROMPT.format(
            existing_memory=existing_memory or "(empty)",
            conversation=conversation,
        )
        new_memory = await llm.generate_memory(synthesis_prompt)

        # Update profile
        await asyncio.to_thread(lambda: db.table("profiles").update({"synthesized_memory": new_memory.strip()}).eq(
            "id", user_id
        ).execute())
        
        return {"status": "synthesized", "memory_length": len(new_memory)}
    except Exception as e:
        logger.error(f"Error in memory synthesis task: {e}")
        return {"status": "error"}

@router.post("/sessions/{session_id}/synthesize_memory")
async def synthesize_session_memory(
    session_id: str,
    authorization: str = Header(...),
):
    """Trigger memory synthesis for a completed chat session."""
    user_id = _extract_user_id(authorization)
    return await _synthesize_memory_task(session_id, user_id)


# ── Intent Handlers ─────────────────────────────────────────────────────────


def _prepare_search_query(user_message: str, conversation_context: str) -> str:
    """Combine recent context with query if short/pronoun-based for accurate vector search."""
    if conversation_context and (
        len(user_message.split()) < 6
        or any(p in user_message.lower() for p in ["his", "her", "their", "he", "she", "this", "that", "it", "him"])
    ):
        lines = [line.strip() for line in conversation_context.strip().split("\n") if line.strip()]
        last_turns = " ".join(lines[-2:]) if len(lines) >= 2 else conversation_context
        return f"{last_turns} {user_message}"
    return user_message


async def _handle_department_query(
    llm: Any,
    user_message: str,
    conversation_context: str,
    memory_context: str,
    search_keywords: list[str] = None,
) -> str:
    """Handle department-specific queries using RAG retrieval."""
    db = get_supabase_client()

    # Expand query with recent context for follow-up turns
    search_query = _prepare_search_query(user_message, conversation_context)
    query_embedding = await llm.embed_query(search_query)

    # Retrieve relevant chunks via pgvector similarity search
    match_result = db.rpc(
        "match_chunks",
        {
            "query_embedding": query_embedding,
            "match_threshold": 0.2,
            "match_count": 30,
        },
    ).execute()
    
    # Hybrid fallback: exact keyword search for proper nouns / rare words
    import re
    # Supplement LLM intent keywords with regex extraction to guarantee proper nouns aren't missed
    stop_words = {"what", "when", "where", "which", "who", "whom", "whose", "why", "how", "this", "that", "these", "those", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "shall", "should", "can", "could", "may", "might", "must", "about", "above", "across", "after", "against", "along", "among", "around", "at", "before", "behind", "below", "beneath", "beside", "between", "beyond", "but", "by", "concerning", "considering", "despite", "down", "during", "except", "for", "from", "in", "inside", "into", "like", "near", "of", "off", "on", "onto", "out", "outside", "over", "past", "regarding", "round", "since", "through", "throughout", "till", "to", "toward", "under", "underneath", "until", "up", "upon", "with", "within", "without", "number", "email", "office", "chamber", "room", "department", "csis", "bits", "pilani", "user", "assistant", "provided", "context", "documents", "according", "located", "information", "found", "source", "relevance", "based", "contact"}
    extracted = [w for w in set(re.findall(r'\b[a-zA-Z]{4,}\b', search_query)) if w.lower() not in stop_words]
    raw_kws = (search_keywords or []) + extracted
    keywords = list(set([k.lower() for k in raw_kws if k and len(k) > 2]))
    
    hybrid_chunks = []
    if keywords:
        ignore_kws = {"prof", "professor", "dr", "room", "chamber", "email", "number", "course", "syllabus", "list", "all", "the", "and"}
        filtered_kws = [kw for kw in keywords if kw not in ignore_kws]
        if not filtered_kws:
            filtered_kws = keywords

        for kw in filtered_kws:
            # fetch up to 5 chunks to ensure we don't miss the one containing the actual target
            kw_resp = db.table("rag_chunks").select("id, content").ilike("content", f"%{kw}%").limit(5).execute()
            if kw_resp.data:
                for kw_chunk in kw_resp.data:
                    kw_chunk["similarity"] = 0.99
                    kw_chunk["file_name"] = "Keyword Search Match"
                    # Pass the entire chunk to preserve table headers and surrounding context!
                    hybrid_chunks.append(kw_chunk)
                
    # Combine results
    all_chunks = hybrid_chunks + (match_result.data or [])
    # Deduplicate by content
    seen_content = set()
    unique_chunks = []
    for c in all_chunks:
        if c["content"] not in seen_content:
            seen_content.add(c["content"])
            unique_chunks.append(c)

    # Build RAG context
    if unique_chunks:
        rag_context = "\n\n---\n\n".join(
            f"**Source: {chunk['file_name']}** (Relevance: {chunk['similarity']:.2f})\n{chunk['content']}"
            for chunk in unique_chunks[:20]
        )
    else:
        rag_context = "(No relevant documents found in the knowledge base.)"

    system_prompt = DEPARTMENT_RAG_SYSTEM_PROMPT.format(
        memory_context=memory_context,
        rag_context=rag_context,
    )

    if conversation_context.strip():
        full_prompt = f"Previous conversation for context:\n{conversation_context}\n\n---\n\nCurrent question: {user_message}"
    else:
        full_prompt = f"Current question: {user_message}"
    
    return await llm.generate(full_prompt, system_prompt=system_prompt)


async def _handle_department_query_stream(
    llm: Any,
    user_message: str,
    conversation_context: str,
    memory_context: str,
    search_keywords: list[str] = None,
):
    """Handle department-specific queries using RAG retrieval and stream the response."""
    db = get_supabase_client()

    search_query = _prepare_search_query(user_message, conversation_context)
    query_embedding = await llm.embed_query(search_query)
    match_result = db.rpc(
        "match_chunks",
        {
            "query_embedding": query_embedding,
            "match_threshold": 0.2,
            "match_count": 30,
        },
    ).execute()
    
    # Hybrid fallback: exact keyword search for proper nouns / rare words
    import re
    # Supplement LLM intent keywords with regex extraction to guarantee proper nouns aren't missed
    stop_words = {"what", "when", "where", "which", "who", "whom", "whose", "why", "how", "this", "that", "these", "those", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "shall", "should", "can", "could", "may", "might", "must", "about", "above", "across", "after", "against", "along", "among", "around", "at", "before", "behind", "below", "beneath", "beside", "between", "beyond", "but", "by", "concerning", "considering", "despite", "down", "during", "except", "for", "from", "in", "inside", "into", "like", "near", "of", "off", "on", "onto", "out", "outside", "over", "past", "regarding", "round", "since", "through", "throughout", "till", "to", "toward", "under", "underneath", "until", "up", "upon", "with", "within", "without", "number", "email", "office", "chamber", "room", "department", "csis", "bits", "pilani", "user", "assistant", "provided", "context", "documents", "according", "located", "information", "found", "source", "relevance", "based", "contact"}
    extracted = [w for w in set(re.findall(r'\b[a-zA-Z]{4,}\b', search_query)) if w.lower() not in stop_words]
    raw_kws = (search_keywords or []) + extracted
    keywords = list(set([k.lower() for k in raw_kws if k and len(k) > 2]))
    
    hybrid_chunks = []
    if keywords:
        ignore_kws = {"prof", "professor", "dr", "room", "chamber", "email", "number", "course", "syllabus", "list", "all", "the", "and"}
        filtered_kws = [kw for kw in keywords if kw not in ignore_kws]
        if not filtered_kws:
            filtered_kws = keywords

        for kw in filtered_kws:
            # fetch up to 5 chunks to ensure we don't miss the one containing the actual target
            kw_resp = db.table("rag_chunks").select("id, content").ilike("content", f"%{kw}%").limit(5).execute()
            if kw_resp.data:
                for kw_chunk in kw_resp.data:
                    kw_chunk["similarity"] = 0.99
                    kw_chunk["file_name"] = "Keyword Search Match"
                    # Pass the entire chunk to preserve table headers and surrounding context!
                    hybrid_chunks.append(kw_chunk)
                
    # Combine results
    all_chunks = hybrid_chunks + (match_result.data or [])
    # Deduplicate by content
    seen_content = set()
    unique_chunks = []
    for c in all_chunks:
        if c["content"] not in seen_content:
            seen_content.add(c["content"])
            unique_chunks.append(c)

    if unique_chunks:
        rag_context = "\n\n---\n\n".join(
            f"**Source: {chunk['file_name']}** (Relevance: {chunk['similarity']:.2f})\n{chunk['content']}"
            for chunk in unique_chunks[:20]
        )
    else:
        rag_context = "(No relevant documents found in the knowledge base.)"

    system_prompt = DEPARTMENT_RAG_SYSTEM_PROMPT.format(
        memory_context=memory_context,
        rag_context=rag_context,
    )

    if conversation_context.strip():
        full_prompt = f"Previous conversation for context:\n{conversation_context}\n\n---\n\nCurrent question: {user_message}"
    else:
        full_prompt = f"Current question: {user_message}"
    
    async for chunk in llm.generate_stream(full_prompt, system_prompt=system_prompt):
        yield chunk


async def _handle_calendar_query(
    llm: Any,
    user_message: str,
    conversation_context: str,
    memory_context: str,
) -> tuple[str, str | None, dict | None]:
    """Handle room/lab reservation queries.

    Returns:
        Tuple of (response_content, interactive_type, interactive_payload).
    """
    # Query FreeBusy data for all rooms
    availability = await query_freebusy()
    availability_text = await format_availability_for_llm(availability)

    # IST is UTC+5:30
    from datetime import datetime, timezone, timedelta
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    current_time_ist = datetime.now(ist_tz).strftime("%Y-%m-%d %I:%M %p %Z (Offset: +05:30)")

    system_prompt = CALENDAR_SYSTEM_PROMPT.format(
        rooms_manifest=await get_rooms_manifest_text(),
        availability_data=availability_text,
        memory_context=memory_context,
        current_time_ist=current_time_ist,
    )

    full_prompt = f"Conversation history:\n{conversation_context}\n\nCurrent request: {user_message}"
    response = await llm.generate(full_prompt, system_prompt=system_prompt)

    # Extract booking proposal if present
    interactive_type = None
    interactive_payload = None

    proposal_match = re.search(
        r"```booking_proposal\s*\n([\s\S]*?)\n\s*```", response
    )
    if proposal_match:
        try:
            proposal_data = json.loads(proposal_match.group(1).strip())
            interactive_type = "booking_proposal"
            interactive_payload = proposal_data
            # Remove the raw JSON block from the displayed content
            response = re.sub(
                r"```booking_proposal\s*\n[\s\S]*?\n\s*```",
                "",
                response,
            ).strip()
        except json.JSONDecodeError:
            logger.warning("Failed to parse booking proposal JSON from LLM response")

    return response, interactive_type, interactive_payload


async def _handle_general_query(
    llm: Any,
    user_message: str,
    conversation_context: str,
    memory_context: str,
) -> str:
    """Handle general CS/academic queries with no RAG, appending a disclaimer."""
    system_prompt = GENERAL_QUERY_SYSTEM_PROMPT.format(memory_context=memory_context)
    full_prompt = f"Conversation history:\n{conversation_context}\n\nCurrent question: {user_message}"
    return await llm.generate(full_prompt, system_prompt=system_prompt)


async def _handle_general_query_stream(
    llm: Any,
    user_message: str,
    conversation_context: str,
    memory_context: str,
):
    """Handle general CS/academic queries and stream the response."""
    system_prompt = GENERAL_QUERY_SYSTEM_PROMPT.format(memory_context=memory_context)
    full_prompt = f"Conversation history:\n{conversation_context}\n\nCurrent question: {user_message}"
    async for chunk in llm.generate_stream(full_prompt, system_prompt=system_prompt):
        yield chunk
