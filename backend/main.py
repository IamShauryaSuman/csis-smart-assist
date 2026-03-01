import smtplib
from datetime import timedelta
from datetime import datetime, timezone
from email.message import EmailMessage
from uuid import UUID
from zoneinfo import ZoneInfo
from calender.functions import *
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.chat_service import ChatService
from app.config import get_settings
from app.rag_local_ingest import sync_local_rag_data_folder
from calender.client import get_calendar_client, parse_start_iso
from calender.functions import create_event, find_nearby_free_slots, is_slot_available
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


def _send_email_notification(
    recipients: list[str],
    subject: str,
    body: str,
) -> None:
    smtp_sender_email = settings.smtp_sender_email
    smtp_sender_password = settings.smtp_sender_password
    if not smtp_sender_email or not smtp_sender_password:
        return

    normalized_recipients = sorted(
        {item.strip() for item in recipients if item and item.strip()})
    if not normalized_recipients:
        return

    message = EmailMessage()
    message["From"] = smtp_sender_email
    message["To"] = ", ".join(normalized_recipients)
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as smtp_client:
        smtp_client.login(smtp_sender_email, smtp_sender_password)
        smtp_client.send_message(message)


def _parse_booking_slot_to_utc(date_value: str, time_slot: str) -> tuple[datetime, datetime]:
    try:
        start_text, end_text = [part.strip()
                                for part in time_slot.split("-", 1)]
        if len(start_text) == 5:
            start_text = f"{start_text}:00"
        if len(end_text) == 5:
            end_text = f"{end_text}:00"
        local_timezone = ZoneInfo("Asia/Kolkata")
        start_local = datetime.fromisoformat(
            f"{date_value}T{start_text}").replace(tzinfo=local_timezone)
        end_local = datetime.fromisoformat(
            f"{date_value}T{end_text}").replace(tzinfo=local_timezone)
        if end_local <= start_local:
            raise ValueError("End time must be after start time")
        return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail="Invalid booking time_slot format") from exc


def get_supabase_service() -> SupabaseService:
    client = get_supabase_client()
    return SupabaseService(client=client, vector_dimensions=settings.vector_dimensions)


def get_chat_service(
    service: SupabaseService = Depends(get_supabase_service),
) -> ChatService:
    return ChatService(settings=settings, supabase_service=service)


@app.on_event("startup")
def startup_ingest_local_rag_data() -> None:
    if not settings.rag_auto_ingest_local_data:
        return

    try:
        service = get_supabase_service()
        summary = sync_local_rag_data_folder(
            service=service,
            data_dir=settings.rag_local_data_dir,
            vector_dimensions=settings.vector_dimensions,
        )
        print("[RAG] local data sync summary:", summary)
    except Exception as exc:
        print(f"[RAG] local data sync failed: {exc}")


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
    booking = service.create_booking_request(payload)

    # admin_seed_emails = {
    #     item.strip().lower()
    #     for item in settings.admin_seed_emails.split(",")
    #     if item.strip()
    # }
    # admin_emails = set(service.list_admin_emails())
    # admin_emails.update(admin_seed_emails)

    requester = service.get_user_by_id(payload.requester_user_id)
    requester_label = requester.get(
        "email") if requester else str(payload.requester_user_id)
    # _send_email_notification(
    #     recipients=list(admin_emails),
    #     subject=f"[CSIS SmartAssist] New booking request {booking['id']}",
    #     body=(
    #         "A new booking request has been created.\n\n"
    #         f"Request ID: {booking['id']}\n"
    #         f"Requester: {requester_label}\n"
    #         f"Resource: {booking['resource']}\n"
    #         f"Date: {booking['date']}\n"
    #         f"Time slot: {booking['time_slot']}\n"
    #         f"Purpose: {booking['purpose']}\n"
    #         f"Participants: {booking['participants']}\n"
    #     ),
    # )
    send_email(
        email_receiver="f20240521@goa.bits-pilani.ac.in",
        subject=f"[CSIS SmartAssist] New booking request {booking['id']}",
        body=(
            "A new booking request has been created.\n\n"
            f"Request ID: {booking['id']}\n"
            f"Requester: {requester_label}\n"
            f"Resource: {booking['resource']}\n"
            f"Date: {booking['date']}\n"
            f"Time slot: {booking['time_slot']}\n"
            f"Purpose: {booking['purpose']}\n"
            f"Participants: {booking['participants']}\n"
        ),
    )

    return booking


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
    current_booking = service.get_booking_request_by_id(request_id)
    calendar_event_link: str | None = None

    if payload.status == BookingStatus.accepted:
        start_time, end_time = _parse_booking_slot_to_utc(
            date_value=str(current_booking["date"]),
            time_slot=str(current_booking["time_slot"]),
        )
        calendar_service, calendar_id = get_calendar_client(settings)
        calendar_event = create_event(
            service=calendar_service,
            calendarID=calendar_id,
            start_time=start_time,
            end_time=end_time,
            title=f"Booking: {current_booking['resource']}",
            description=(
                f"Request ID: {current_booking['id']}\n"
                f"Purpose: {current_booking['purpose']}\n"
                f"Participants: {current_booking['participants']}\n"
                f"Remarks: {payload.remarks or current_booking.get('remarks') or '-'}"
            ),
            location=current_booking["resource"],
        )
        calendar_event_link = calendar_event.get("htmlLink")

    updated_booking = service.decide_booking_request(
        request_id=request_id, payload=payload)

    requester = service.get_user_by_id(updated_booking["requester_user_id"])
    if requester and requester.get("email"):
        decision_word = "approved" if payload.status == BookingStatus.accepted else "declined"
        body = (
            "Your CSIS SmartAssist booking request has been reviewed.\n\n"
            f"Request ID: {updated_booking['id']}\n"
            f"Status: {decision_word}\n"
            f"Resource: {updated_booking['resource']}\n"
            f"Date: {updated_booking['date']}\n"
            f"Time slot: {updated_booking['time_slot']}\n"
            f"Remarks: {payload.remarks or '-'}\n"
        )
        if calendar_event_link:
            body += f"\nCalendar event: {calendar_event_link}\n"

        send_email(
            email_receiver=requester["email"],
            subject=f"[CSIS SmartAssist] Booking request {decision_word}",
            body=body,
        )

    if calendar_event_link:
        updated_booking["calendar_event_link"] = calendar_event_link

    return updated_booking


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


@app.post("/rag/ingest-local")
def ingest_local_rag_data(
    service: SupabaseService = Depends(get_supabase_service),
) -> dict:
    return sync_local_rag_data_folder(
        service=service,
        data_dir=settings.rag_local_data_dir,
        vector_dimensions=settings.vector_dimensions,
    )


@app.post("/chat", response_model=ChatResponseOut)
def chat(
    payload: ChatRequestIn,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponseOut:
    return service.answer_query(query=payload.query, user_id=payload.user_id)


@app.post("/calendar/availability")
def calendar_availability(
    payload: CalendarAvailabilityIn,
) -> dict:
    service, calendar_id = get_calendar_client(settings)
    start_time = parse_start_iso(payload.start_iso)
    end_time = start_time + timedelta(minutes=payload.duration_minutes)
    available = is_slot_available(
        start_time=start_time,
        per=payload.duration_minutes,
        service=service,
        calenderID=calendar_id,
    )

    return {
        "calendar_id": calendar_id,
        "start_iso": start_time.isoformat(),
        "end_iso": end_time.isoformat(),
        "available": available,
    }


@app.post("/calendar/nearby-slots")
def calendar_nearby_slots(
    payload: CalendarNearbyIn,
) -> dict:
    service, calendar_id = get_calendar_client(settings)
    start_time = parse_start_iso(payload.start_iso)

    free_slots = find_nearby_free_slots(
        start_time=start_time,
        per=payload.duration_minutes,
        service=service,
        calendarID=calendar_id,
        window_hours=payload.window_hours,
        step_minutes=payload.step_minutes,
    )

    return {
        "calendar_id": calendar_id,
        "requested_start_iso": start_time.isoformat(),
        "duration_minutes": payload.duration_minutes,
        "window_hours": payload.window_hours,
        "free_slots": [
            {
                "start_iso": slot_start.isoformat(),
                "end_iso": slot_end.isoformat(),
            }
            for slot_start, slot_end in free_slots
        ],
    }
