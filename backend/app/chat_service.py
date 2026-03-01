import json
from datetime import datetime, timedelta
from functools import lru_cache
from importlib import import_module
from typing import Any

from fastapi import HTTPException

from calender.client import get_calendar_client, parse_start_iso
from calender.functions import find_nearby_free_slots, is_slot_available
from .config import Settings
from .schemas import CalendarFlowOut, CalendarSlotOut, ChatResponseOut
from .services import SupabaseService


@lru_cache
def get_embed_model():
    try:
        sentence_transformers = import_module("sentence_transformers")
        sentence_transformer_cls = sentence_transformers.SentenceTransformer
    except Exception:
        return None
    return sentence_transformer_cls("intfloat/e5-base-v2")


class ChatService:
    def __init__(self, settings: Settings, supabase_service: SupabaseService) -> None:
        self.settings = settings
        self.supabase_service = supabase_service

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
        rag_rows: list[dict[str, Any]] = []
        embed_model = get_embed_model()
        if embed_model is not None:
            try:
                embedding = embed_model.encode([f"query: {query}"])[0].tolist()
                rag_rows = self.supabase_service.search_rag_chunks_from_embedding(
                    embedding=embedding,
                    match_count=5,
                )
            except Exception:
                rag_rows = []

        if not rag_rows:
            rag_rows = self.supabase_service.search_rag_chunks_by_text(
                query=query,
                match_count=5,
            )

        context = "\n".join(row.get("content", "")
                            for row in rag_rows if row.get("content"))

        prompt = f"""
You are CSIS SmartAssist. Answer the user query using the context below.
If context is insufficient, give a helpful next step and do not mention internal system details.
If the user asks for a form, provide the exact form/link if present in context; otherwise tell them who to contact.

User ID: {user_id}

Context:
{context}

Question:
{query}
"""
        answer = self._generate_answer(prompt)
        if answer == "__LLM_QUOTA_EXCEEDED__":
            raise HTTPException(
                status_code=429,
                detail="Language model quota exceeded. Please retry later or update Gemini billing/quota.",
            )
        if answer == "__LLM_UNAVAILABLE__":
            raise HTTPException(
                status_code=503,
                detail="Language model service is currently unavailable.",
            )
        sources = [
            {
                "document_id": row.get("document_id"),
                "chunk_index": row.get("chunk_index"),
                "similarity": row.get("similarity"),
            }
            for row in rag_rows
        ]
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
                resource=location or None,
            )
            available = is_slot_available(
                start_time=start_time,
                per=duration_minutes,
                service=service,
                calenderID=calendar_id,
            )
            if available:
                answer = (
                    f"That slot{location_text} is available. Start: {start_time.isoformat()}, "
                    f"duration: {duration_minutes} minutes. Do you want me to create the booking request?"
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
            nearby_slots = [
                CalendarSlotOut(
                    start_iso=slot_start.isoformat(),
                    end_iso=slot_end.isoformat(),
                    duration_minutes=duration_minutes,
                    resource=location or None,
                )
                for slot_start, slot_end in nearby[:5]
            ]

            if nearby_slots:
                options = ", ".join(
                    f"{slot_item.start_iso} to {slot_item.end_iso}"
                    for slot_item in nearby_slots
                )
                answer = (
                    f"That slot{location_text} is not available. "
                    f"Nearby options: {options}."
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

        now = datetime.utcnow().isoformat() + "+00:00"
        start_time = parse_start_iso(now)
        nearby = find_nearby_free_slots(
            start_time=start_time,
            per=duration_minutes,
            service=service,
            calendarID=calendar_id,
            window_hours=3,
            step_minutes=duration_minutes,
        )
        if nearby:
            options = ", ".join(
                f"{slot_start.isoformat()} to {slot_end.isoformat()}"
                for slot_start, slot_end in nearby[:5]
            )
            return ChatResponseOut(
                answer=(
                    f"I could not detect an exact date/time in your message{location_text}. "
                    f"Nearby available slots: {options}."
                ),
                sources=[],
                intent="calendar_query",
                calendar_flow=CalendarFlowOut(
                    status="missing_datetime",
                    requested_slot=None,
                    nearby_slots=[
                        CalendarSlotOut(
                            start_iso=slot_start.isoformat(),
                            end_iso=slot_end.isoformat(),
                            duration_minutes=duration_minutes,
                            resource=location or None,
                        )
                        for slot_start, slot_end in nearby[:5]
                    ],
                    requires_user_approval=False,
                ),
            )
        return ChatResponseOut(
            answer=(
                f"I could not detect an exact date/time in your message{location_text}, "
                "and I could not find nearby free slots."
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

    def _decide_intent(self, query: str) -> dict[str, Any]:
        if not self.settings.gemini_api_key:
            lowered = query.lower()
            if any(word in lowered for word in ("availability", "available", "free slot", "calendar", "schedule", "time", "book", "booking", "reserve", "reservation")):
                return {
                    "intent": "calendar_query",
                    "slot": {
                        "start_iso": None,
                        "duration_minutes": 60,
                        "location": None,
                    },
                }
            return {"intent": "info_query"}

        prompt = f"""
Classify the user message into exactly one intent:
- info_query
- calendar_query

Return strict JSON only with this shape:
{{
  "intent": "info_query|calendar_query",
  "slot": {{
    "start_iso": "ISO8601 datetime with timezone offset or null",
        "duration_minutes": 60,
        "location": "specific room/lab name from user message, or null"
  }}
}}

Rules:
- Use calendar_query for free/busy checks and nearby slot discovery.
- Use info_query for all informational questions.
- If date/time is missing, keep slot.start_iso as null.
- If duration is missing, use 60.
- Extract slot.location when user mentions a specific room/lab (for example: "Lab 3", "Room A-201").

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

    def _generate_answer(self, prompt: str) -> str:
        if not self.settings.gemini_api_key:
            return "I can help with that, but LLM generation is not configured yet."

        try:
            from google import genai
        except Exception:
            return (
                "RAG retrieval succeeded, but optional LLM dependency is missing. "
                "Install backend requirements to enable Gemini generation."
            )

        try:
            client = genai.Client(api_key=self.settings.gemini_api_key)
            model_candidates = [
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-1.5-flash",
            ]
            for model_name in model_candidates:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    if response.text:
                        return response.text
                except Exception as exc:
                    message = str(exc).lower()
                    if "resource_exhausted" in message or "quota" in message or "code': 429" in message or "code\": 429" in message:
                        return "__LLM_QUOTA_EXCEEDED__"
                    continue
            return "__LLM_UNAVAILABLE__"
        except Exception:
            return "__LLM_UNAVAILABLE__"
