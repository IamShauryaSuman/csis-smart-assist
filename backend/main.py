from uuid import UUID

from fastapi import Depends, FastAPI, Query

from app.config import get_settings
from app.schemas import (
    BookingRequestCreateIn,
    BookingRequestDecisionIn,
    BookingStatus,
    RagChunkCreateIn,
    RagDocumentCreateIn,
    RagSearchIn,
    RoleAssignmentIn,
    UserSyncIn,
)
from app.services import SupabaseService
from app.supabase_client import get_supabase_client

app = FastAPI(
    title="CSIS SmartAssist Backend",
    description="Supabase-powered API for users, roles, booking requests, and RAG metadata.",
    version="1.0.0",
)


def get_supabase_service() -> SupabaseService:
    settings = get_settings()
    client = get_supabase_client()
    return SupabaseService(client=client, vector_dimensions=settings.vector_dimensions)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "CSIS SmartAssist backend is running."}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/users/sync")
def sync_user(
    payload: UserSyncIn,
    service: SupabaseService = Depends(get_supabase_service),
) -> dict:
    return service.sync_user(payload)


@app.post("/users/{user_id}/roles")
def assign_role(
    user_id: UUID,
    payload: RoleAssignmentIn,
    service: SupabaseService = Depends(get_supabase_service),
) -> dict:
    return service.assign_role(user_id=user_id, role_name=payload.role_name)


@app.get("/users/{user_id}/roles")
def list_roles(
    user_id: UUID,
    service: SupabaseService = Depends(get_supabase_service),
) -> dict:
    return service.list_user_roles(user_id=user_id)


@app.post("/booking-requests")
def create_booking_request(
    payload: BookingRequestCreateIn,
    service: SupabaseService = Depends(get_supabase_service),
) -> dict:
    return service.create_booking_request(payload)


@app.get("/booking-requests")
def list_booking_requests(
    status: BookingStatus | None = Query(default=None),
    service: SupabaseService = Depends(get_supabase_service),
) -> list[dict]:
    return service.list_booking_requests(status=status)


@app.patch("/booking-requests/{request_id}/decision")
def decide_booking_request(
    request_id: UUID,
    payload: BookingRequestDecisionIn,
    service: SupabaseService = Depends(get_supabase_service),
) -> dict:
    return service.decide_booking_request(request_id=request_id, payload=payload)


@app.post("/rag/documents")
def create_rag_document(
    payload: RagDocumentCreateIn,
    service: SupabaseService = Depends(get_supabase_service),
) -> dict:
    return service.create_rag_document(payload)


@app.post("/rag/chunks")
def create_rag_chunk(
    payload: RagChunkCreateIn,
    service: SupabaseService = Depends(get_supabase_service),
) -> dict:
    return service.create_rag_chunk(payload)


@app.post("/rag/chunks/search")
def search_rag_chunks(
    payload: RagSearchIn,
    service: SupabaseService = Depends(get_supabase_service),
) -> list[dict]:
    return service.search_rag_chunks(payload)
