from datetime import date
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class BookingStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"


class UserSyncIn(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None = None


class RoleAssignmentIn(BaseModel):
    role_name: str = Field(min_length=2, max_length=50)


class BookingRequestCreateIn(BaseModel):
    requester_user_id: UUID
    resource: str = Field(min_length=2, max_length=100)
    date: date
    time_slot: str = Field(min_length=3, max_length=50)
    purpose: str = Field(min_length=2, max_length=300)
    participants: int = Field(ge=1, le=1000)
    remarks: str | None = Field(default=None, max_length=1000)


class BookingRequestDecisionIn(BaseModel):
    status: BookingStatus
    reviewer_user_id: UUID | None = None
    remarks: str | None = Field(default=None, max_length=1000)


class RagDocumentCreateIn(BaseModel):
    title: str = Field(min_length=2, max_length=250)
    source_uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagChunkCreateIn(BaseModel):
    document_id: UUID
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    embedding: list[float]
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagSearchIn(BaseModel):
    embedding: list[float]
    match_count: int = Field(default=5, ge=1, le=50)
