from datetime import date
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class BookingStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"


class UserSyncIn(BaseModel):
    id: UUID | None = None
    email: EmailStr
    full_name: str | None = None


class RoleAssignmentIn(BaseModel):
    role_name: str = Field(min_length=2, max_length=50)


class BookingRequestCreateIn(BaseModel):
    requester_user_id: UUID
    location: str = Field(min_length=2, max_length=100)
    date: date
    time_slot: str = Field(min_length=5, max_length=23)
    purpose: str = Field(min_length=1)
    remarks: str | None = None


class BookingRequestDecisionIn(BaseModel):
    status: BookingStatus
    reviewer_user_id: UUID | None = None
    remarks: str | None = Field(default=None, max_length=1000)


class RagDocumentCreateIn(BaseModel):
    title: str = Field(min_length=1)
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagChunkCreateIn(BaseModel):
    document_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    embedding: list[float] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagSearchIn(BaseModel):
    embedding: list[float]
    match_count: int = Field(default=5, ge=1, le=50)


class RagDriveIngestIn(BaseModel):
    folder_id: str | None = Field(default=None, min_length=1)
    recursive: bool = True
    max_files: int = Field(default=500, ge=1, le=5000)


class ChatRequestIn(BaseModel):
    query: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    session_id: str | None = None


class CalendarSlotOut(BaseModel):
    start_iso: str
    end_iso: str
    duration_minutes: int = Field(ge=15, le=240)
    location: str | None = None


class CalendarFlowOut(BaseModel):
    status: Literal["slot_available", "slot_unavailable", "missing_datetime"]
    requested_slot: CalendarSlotOut | None = None
    nearby_slots: list[CalendarSlotOut] = Field(default_factory=list)
    requires_user_approval: bool = False


class ChatResponseOut(BaseModel):
    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    intent: Literal["info_query", "calendar_query"]
    calendar_flow: CalendarFlowOut | None = None
    assistant_message_id: str | None = None


class CalendarAvailabilityIn(BaseModel):
    start_iso: str
    duration_minutes: int = Field(default=60, ge=15, le=240)


class CalendarNearbyIn(BaseModel):
    start_iso: str
    duration_minutes: int = Field(default=60, ge=15, le=240)
    window_hours: int = Field(default=3, ge=1, le=24)
    step_minutes: int | None = Field(default=None, ge=5, le=240)


# ── Chat history schemas ──────────────────────────────────────────────

class ChatMessageCreateIn(BaseModel):
    content: str
    role: Literal["user", "assistant"]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatMessageUpdateIn(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)



class ChatSessionCreateIn(BaseModel):
    user_email: str = Field(min_length=3)
    title: str = Field(min_length=1, max_length=255)


class ChatMessageOut(BaseModel):
    id: UUID
    chat_session_id: UUID
    content: str
    role: str
    created_at: str


class ChatSessionOut(BaseModel):
    id: UUID
    user_email: str
    title: str
    created_at: str
