import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)
from fastapi import HTTPException

from calender.client import get_calendar_client, parse_start_iso
from calender.functions import find_nearby_free_slots, is_slot_available
from .config import Settings
from .schemas import CalendarFlowOut, CalendarSlotOut, ChatResponseOut
from .services import SupabaseService

# ── Conversation Memory Store ──────────────────────────────────────────
# Sliding window size (number of recent message pairs to keep verbatim)
MEMORY_WINDOW_K = 6

# Per-user memory: { user_id: { "history": [...], "summary": "..." } }
_conversation_memory: dict[str, dict[str, Any]] = defaultdict(
    lambda: {"history": [], "summary": ""}
)


class ChatService:
    def __init__(self, settings: Settings, supabase_service: SupabaseService) -> None:
        self.settings = settings
        self.supabase_service = supabase_service

    def _embed_query(self, text: str) -> list[float]:
        """Generate embeddings using Gemini."""
        return self._embed_query_google(text)

    def _embed_query_google(self, text: str) -> list[float]:
        """Generate 768-dim embeddings using Gemini."""
        if not self.settings.gemini_api_key:
            logger.error("[Gemini Embed] Missing GEMINI_API_KEY")
            return [0.0] * self.settings.vector_dimensions

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.settings.gemini_api_key)
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=text,
                task_type="retrieval_query",
                output_dimensionality=768,
            )
            embedding = result.get("embedding")
            if embedding:
                if isinstance(embedding, list) and embedding and isinstance(embedding[0], list):
                    return embedding[0]
                return embedding

            embeddings = result.get("embeddings")
            if isinstance(embeddings, list) and embeddings:
                first_embedding = embeddings[0]
                if isinstance(first_embedding, list) and first_embedding and isinstance(first_embedding[0], list):
                    return first_embedding[0]
                return first_embedding

            raise ValueError(f"Unexpected Gemini embedding response shape: {result}")
        except Exception as exc:
            logger.error(f"[Gemini Embed] Failed: {exc}")
            return [0.0] * self.settings.vector_dimensions

    def _call_llm(self, prompt: str) -> str:
        """Call the Gemini API."""
        return self._call_gemini(prompt)

    def _call_gemini(self, prompt: str) -> str:
        """Call the Google Gemini API."""
        if not self.settings.gemini_api_key:
            return "Error calling Gemini API: GEMINI_API_KEY is not configured."

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.settings.gemini_api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            return response.text
        except Exception as exc:
            logger.error(f"[Gemini] Error: {exc}", exc_info=True)
            return f"Error calling Gemini API: {exc}. Please check your credentials."

    # ── Memory helpers ─────────────────────────────────────────────────
    def _get_memory(self, user_id: str) -> dict[str, Any]:
        return _conversation_memory[user_id]

    def _append_turn(self, user_id: str, user_msg: str, assistant_msg: str) -> None:
        """Append a (user, assistant) turn and compress when window overflows."""
        mem = self._get_memory(user_id)
        mem["history"].append({"user": user_msg, "assistant": assistant_msg})

        # If history exceeds window, summarize overflow turns
        if len(mem["history"]) > MEMORY_WINDOW_K:
            overflow = mem["history"][:-MEMORY_WINDOW_K]
            mem["history"] = mem["history"][-MEMORY_WINDOW_K:]

            # Build text of overflowing turns
            overflow_text = "\n".join(
                f"User: {t['user']}\nAssistant: {t['assistant']}" for t in overflow
            )
            existing_summary = mem["summary"]
            summary_prompt = (
                "You are a summarizer. Merge the existing conversation summary with the new exchanges below "
                "into a single concise paragraph that preserves all important facts, preferences, and decisions.\n\n"
                f"Existing summary:\n{existing_summary or '(none)'}\n\n"
                f"New exchanges:\n{overflow_text}\n\n"
                "Updated summary:"
            )
            new_summary = self._generate_answer(summary_prompt)
            if new_summary and not new_summary.startswith("__"):
                mem["summary"] = new_summary

    def _build_memory_context(self, user_id: str) -> str:
        """Build a formatted memory block for the LLM prompt."""
        mem = self._get_memory(user_id)
        parts = []
        if mem["summary"]:
            parts.append(
                f"Conversation Summary (older context):\n{mem['summary']}")
        if mem["history"]:
            recent = "\n".join(
                f"User: {t['user']}\nAssistant: {t['assistant']}" for t in mem["history"]
            )
            parts.append(
                f"Recent conversation (last {len(mem['history'])} turns):\n{recent}")
        return "\n---\n".join(parts) if parts else ""

    def answer_query(self, query: str, user_id: str) -> ChatResponseOut:
        try:
            decision = self._decide_intent(query=query)
            intent = decision.get("intent", "info_query")

            if intent == "calendar_query":
                return self._handle_availability_check(query=query, decision=decision)

            return self._handle_info_query(query=query, user_id=user_id)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Chat processing failed: {exc}") from exc

    def _handle_info_query(self, query: str, user_id: str) -> ChatResponseOut:
        # Use local ChromaDB for RAG retrieval instead of Supabase
        rag_chunks: list[str] = []
        sources: list[dict] = []

        try:
            import os
            os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
            import chromadb
            client = chromadb.PersistentClient(path="./RAG_db")
            collection = client.get_or_create_collection(name="RAG_db")

            if collection.count() > 0:
                query_embedding = self._embed_query(query)
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=5,
                )
                if results and "documents" in results and results["documents"]:
                    rag_chunks = results["documents"][0]
                    # Build source info from ChromaDB results
                    for i, doc in enumerate(rag_chunks):
                        sources.append({
                                "document_id": results["ids"][0][i] if results.get("ids") else None,
                                "chunk_index": i,
                                "similarity": round(1 - (results["distances"][0][i] if results.get("distances") else 0), 4),
                            })
        except Exception as exc:
            print(f"[ChromaDB] retrieval error: {exc}")
            rag_chunks = []

        context = "\n".join(
            rag_chunks) if rag_chunks else "No relevant documents found."

        # Build conversation memory context
        memory_context = self._build_memory_context(user_id)
        memory_block = f"\nConversation Memory:\n---\n{memory_context}\n---\n" if memory_context else ""

        prompt = f"""
You are CSIS SmartAssist. Answer the user query using the document context and conversation memory below.
If context is insufficient, give a helpful next step and do not mention internal system details.
If the user asks for a form, provide the exact form/link if present in context; otherwise tell them who to contact.
If your answer contains or references a link from the context, ALWAYS include the link in your response and format it cleanly as a Markdown link.
Use conversation memory to maintain continuity — reference earlier topics if relevant.

User ID: {user_id}
{memory_block}
Document Context:
{context}

Question:
{query}
"""
        answer = self._generate_answer(prompt)
        if answer == "__LLM_QUOTA_EXCEEDED__":
            raise HTTPException(
                status_code=429,
                detail="Language model quota exceeded. Please retry later.",
            )
        if answer == "__LLM_UNAVAILABLE__":
            raise HTTPException(
                status_code=503,
                detail="Language model service is currently unavailable.",
            )

        # Save this turn to memory
        self._append_turn(user_id, query, answer)

        return ChatResponseOut(answer=answer, sources=sources, intent="info_query")

    def _handle_availability_check(self, query: str, decision: dict[str, Any]) -> ChatResponseOut:
        slot = decision.get("slot", {})
        start_iso = slot.get("start_iso")
        location = str(slot.get("location") or "").strip()
        location_text = f" for {location}" if location else ""
        try:
            duration_minutes = int(slot.get("duration_minutes") or 60)
        except (TypeError, ValueError):
            duration_minutes = 60

        try:
            service, calendar_id = get_calendar_client(self.settings)
        except Exception:
            return ChatResponseOut(
                answer=(
                    "Calendar service is currently unavailable. I can still help with policy or information "
                    "questions, or you can retry booking in a moment."
                ),
                sources=[],
                intent="calendar_query",
                calendar_flow=CalendarFlowOut(
                    status="missing_datetime",
                    requested_slot=None,
                    nearby_slots=[],
                    requires_user_approval=False,
                ),
            )

        if start_iso:
            start_time = parse_start_iso(start_iso)
            requested_slot = CalendarSlotOut(
                start_iso=start_time.isoformat(),
                end_iso=(start_time +
                         timedelta(minutes=duration_minutes)).isoformat(),
                duration_minutes=duration_minutes,
                location=location or None,
            )
            available = is_slot_available(
                start_time=start_time,
                per=duration_minutes,
                service=service,
                calenderID=calendar_id,
            )
            if available:
                ist = ZoneInfo("Asia/Kolkata")
                display_start = start_time.astimezone(ist)
                display_date = display_start.strftime("%B %d, %Y")
                display_time = display_start.strftime("%I:%M %p")
                answer = (
                    f"That slot{location_text} is available. "
                    f"Date: {display_date}, Start: {display_time} IST, "
                    f"Duration: {duration_minutes} minutes. "
                    f"Do you want me to create the booking request?"
                )
                return ChatResponseOut(
                    answer=answer,
                    sources=[],
                    intent="calendar_query",
                    calendar_flow=CalendarFlowOut(
                        status="slot_available",
                        requested_slot=requested_slot,
                        nearby_slots=[],
                        requires_user_approval=True,
                    ),
                )

            nearby = find_nearby_free_slots(
                start_time=start_time,
                per=duration_minutes,
                service=service,
                calendarID=calendar_id,
                window_hours=3,
                step_minutes=duration_minutes,
            )
            ist = ZoneInfo("Asia/Kolkata")
            nearby_slots = [
                CalendarSlotOut(
                    start_iso=slot_start.isoformat(),
                    end_iso=slot_end.isoformat(),
                    duration_minutes=duration_minutes,
                    location=location or None,
                )
                for slot_start, slot_end in nearby[:5]
            ]

            if nearby_slots:
                options = ", ".join(
                    f"{datetime.fromisoformat(s.start_iso).astimezone(ist).strftime('%b %d %I:%M %p')} - "
                    f"{datetime.fromisoformat(s.end_iso).astimezone(ist).strftime('%I:%M %p')} IST"
                    for s in nearby_slots
                )
                answer = (
                    f"That slot{location_text} is not available. "
                    f"Here are some nearby options: {options}."
                )
            else:
                answer = (
                    f"That slot{location_text} is not available, and no nearby free "
                    "slots were found in the next/previous 3 hours."
                )

            return ChatResponseOut(
                answer=answer,
                sources=[],
                intent="calendar_query",
                calendar_flow=CalendarFlowOut(
                    status="slot_unavailable",
                    requested_slot=requested_slot,
                    nearby_slots=nearby_slots,
                    requires_user_approval=False,
                ),
            )

        # Date/time is missing — ask the user to provide it
        answer = (
            f"To book{location_text}, I need a few details:\n"
            f"1. **Date** (e.g. March 5, tomorrow)\n"
            f"2. **Time** (e.g. 3:00 PM to 5:00 PM)\n"
            f"3. **Purpose** (e.g. Extra Tutorial, Lab session)\n\n"
            f"Please provide these so I can check availability."
        )
        return ChatResponseOut(
            answer=answer,
            sources=[],
            intent="calendar_query",
            calendar_flow=CalendarFlowOut(
                status="missing_datetime",
                requested_slot=None,
                nearby_slots=[],
                requires_user_approval=False,
            ),
        )

    def _decide_intent(self, query: str) -> dict[str, Any]:
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        current_date_str = now.strftime("%Y-%m-%d")
        current_time_str = now.strftime("%H:%M:%S")
        tomorrow_date_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        prompt = f"""
Classify the user message into exactly one intent:
- info_query
- calendar_query

Current date: {current_date_str}
Current time: {current_time_str}
Timezone: Asia/Kolkata (+05:30)
Tomorrow's date: {tomorrow_date_str}

Return strict JSON only with this shape:
{{
  "intent": "info_query|calendar_query",
  "slot": {{
    "start_iso": "ISO8601 datetime with timezone offset +05:30, or null",
        "duration_minutes": 60,
        "location": "specific room/lab name from user message, or null",
        "purpose": "booking purpose from user message, or null"
  }}
}}

Rules:
- Use calendar_query for free/busy checks and nearby slot discovery.
- Use info_query for all informational questions.
- If date/time is missing, keep slot.start_iso as null.
- If duration is missing, use 60.
- Resolve relative dates like "tomorrow" using the current date above.
- Always use timezone offset +05:30 for Asia/Kolkata.
- Extract slot.location when user mentions a specific room/lab (for example: "Lab 3", "Room A-201", "A603").
- Extract slot.purpose when user mentions a reason (for example: "Extra Tutorial", "Lab session", "Meeting").

User message:
{query}
"""
        parsed = self._generate_json(prompt)
        intent = parsed.get("intent")
        if intent not in {"info_query", "calendar_query"}:
            return {"intent": "info_query"}
        return parsed

    def _generate_json(self, prompt: str) -> dict[str, Any]:
        text = self._generate_answer(prompt).strip()

        try:
            return json.loads(text)
        except Exception:
            pass

        if "```" in text:
            fenced = text.split("```")
            for block in fenced:
                block = block.strip()
                if block.startswith("json"):
                    block = block[4:].strip()
                if not block.startswith("{"):
                    continue
                try:
                    return json.loads(block)
                except Exception:
                    continue

        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            candidate = text[first:last + 1]
            try:
                return json.loads(candidate)
            except Exception:
                pass

        return {"intent": "info_query"}

    def _search_context(self, query_embedding: list[float]) -> list[dict[str, Any]]:
        """Search for context using ChromaDB (local) or Supabase (cloud)."""
        # 1. Try local ChromaDB first
        try:
            from .rag_store import search_rag_collection
            matches = search_rag_collection(query_embedding=query_embedding)
            if matches:
                return matches
        except Exception as exc:
            logger.warning(f"[ChromaDB] Search failed or empty, trying Supabase: {exc}")

        # 2. Fallback to Supabase Vector
        try:
            return self.supabase_service.search_rag_chunks_by_embedding(query_embedding)
        except Exception as exc:
            logger.error(f"[Supabase RAG] Search failed: {exc}")
            return []

    def _generate_answer(self, prompt: str) -> str:
        return self._call_llm(prompt)
