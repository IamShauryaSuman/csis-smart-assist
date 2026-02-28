from uuid import UUID

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app.calendar_service import CalendarService
from app.chat_service import ChatService
from app.config import get_settings
from app.schemas import (
    BookingRequestCreateIn,
    BookingRequestDecisionIn,
    BookingStatus,
    CalendarAvailabilityIn,
    CalendarNearbyIn,
    ChatRequestIn,
    ChatResponseOut,
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

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_supabase_service() -> SupabaseService:
    client = get_supabase_client()
    return SupabaseService(client=client, vector_dimensions=settings.vector_dimensions)


def get_chat_service(
    service: SupabaseService = Depends(get_supabase_service),
) -> ChatService:
    return ChatService(settings=settings, supabase_service=service)


def get_calendar_service() -> CalendarService:
    return CalendarService(settings=settings)


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


@app.post("/users/sync-session")
def sync_session_user(
    payload: UserSyncIn,
    service: SupabaseService = Depends(get_supabase_service),
) -> dict:
    user = service.sync_user(payload)
    admin_seed_emails = {
        item.strip().lower()
        for item in settings.admin_seed_emails.split(",")
        if item.strip()
    }
    roles = service.ensure_user_roles(
        user_id=UUID(user["id"]),
        email=user["email"],
        admin_seed_emails=admin_seed_emails,
    )
    return {
        "user": user,
        "roles": roles,
    }


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


@app.get("/users/roles/by-email")
def list_roles_by_email(
    email: str,
    service: SupabaseService = Depends(get_supabase_service),
) -> dict:
    return service.list_user_roles_by_email(email=email)


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


@app.post("/chat", response_model=ChatResponseOut)
def chat(
    payload: ChatRequestIn,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponseOut:
    return service.answer_query(query=payload.query, user_id=payload.user_id)


@app.post("/calendar/availability")
def calendar_availability(
    payload: CalendarAvailabilityIn,
    service: CalendarService = Depends(get_calendar_service),
) -> dict:
    return service.is_slot_available(
        start_iso=payload.start_iso,
        duration_minutes=payload.duration_minutes,
    )


@app.post("/calendar/nearby-slots")
def calendar_nearby_slots(
    payload: CalendarNearbyIn,
    service: CalendarService = Depends(get_calendar_service),
) -> dict:
    return service.find_nearby_free_slots(
        start_iso=payload.start_iso,
        duration_minutes=payload.duration_minutes,
        window_hours=payload.window_hours,
        step_minutes=payload.step_minutes,
    )
