from datetime import UTC, datetime
import re
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid5

from fastapi import HTTPException
from supabase import Client

from .schemas import (
    BookingRequestCreateIn,
    BookingRequestDecisionIn,
    BookingStatus,
    RagSearchIn,
    UserSyncIn,
)


class SupabaseService:
    def __init__(self, client: Client, vector_dimensions: int) -> None:
        self.client = client
        self.vector_dimensions = vector_dimensions

    def sync_user(self, payload: UserSyncIn) -> dict:
        resolved_id = payload.id or uuid5(NAMESPACE_DNS, payload.email.lower())
        response = (
            self.client.table("app_users")
            .upsert(
                {
                    "id": str(resolved_id),
                    "email": payload.email,
                    "full_name": payload.full_name,
                },
                on_conflict="email",
            )
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to sync user")
        return response.data[0]

    def _get_or_create_role(self, role_name: str) -> dict:
        normalized_name = role_name.strip().lower()
        response = (
            self.client.table("roles")
            .select("id,name")
            .eq("name", normalized_name)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]

        created = (
            self.client.table("roles")
            .insert({"name": normalized_name})
            .execute()
        )
        if not created.data:
            raise HTTPException(
                status_code=500, detail="Failed to create role")
        return created.data[0]

    def assign_role(self, user_id: UUID, role_name: str) -> dict:
        role = self._get_or_create_role(role_name)
        response = (
            self.client.table("user_roles")
            .upsert(
                {
                    "user_id": str(user_id),
                    "role_id": role["id"],
                },
                on_conflict="user_id,role_id",
            )
            .execute()
        )
        if response.data is None:
            raise HTTPException(
                status_code=500, detail="Failed to assign role")
        return {"user_id": str(user_id), "role": role["name"]}

    def list_user_roles(self, user_id: UUID) -> dict:
        response = (
            self.client.table("user_roles")
            .select("roles(name)")
            .eq("user_id", str(user_id))
            .execute()
        )

        role_names = [
            row["roles"]["name"]
            for row in (response.data or [])
            if row.get("roles") and row["roles"].get("name")
        ]
        return {"user_id": str(user_id), "roles": role_names}

    def list_user_roles_by_email(self, email: str) -> dict:
        user_response = (
            self.client.table("app_users")
            .select("id,email")
            .eq("email", email)
            .limit(1)
            .execute()
        )

        if not user_response.data:
            return {"user_id": None, "email": email, "roles": []}

        user = user_response.data[0]
        roles_result = self.list_user_roles(UUID(user["id"]))
        return {
            "user_id": user["id"],
            "email": user["email"],
            "roles": roles_result["roles"],
        }

    def get_user_by_id(self, user_id: UUID | str) -> dict | None:
        response = (
            self.client.table("app_users")
            .select("id,email,full_name")
            .eq("id", str(user_id))
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return response.data[0]

    def get_booking_request_by_id(self, request_id: UUID | str) -> dict:
        response = (
            self.client.table("booking_requests")
            .select("*")
            .eq("id", str(request_id))
            .limit(1)
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=404, detail="Booking request not found")
        return response.data[0]

    def list_admin_emails(self) -> list[str]:
        role_response = (
            self.client.table("roles")
            .select("id")
            .eq("name", "admin")
            .limit(1)
            .execute()
        )
        if not role_response.data:
            return []

        admin_role_id = role_response.data[0]["id"]
        user_roles_response = (
            self.client.table("user_roles")
            .select("user_id")
            .eq("role_id", admin_role_id)
            .execute()
        )
        user_ids = [row["user_id"] for row in (
            user_roles_response.data or []) if row.get("user_id")]
        if not user_ids:
            return []

        users_response = (
            self.client.table("app_users")
            .select("email")
            .in_("id", user_ids)
            .execute()
        )
        return [
            row["email"]
            for row in (users_response.data or [])
            if row.get("email")
        ]

    def ensure_user_roles(
        self,
        user_id: UUID,
        email: str,
        admin_seed_emails: set[str] | None = None,
    ) -> list[str]:
        self.assign_role(user_id=user_id, role_name="user")

        if admin_seed_emails and email.lower() in admin_seed_emails:
            self.assign_role(user_id=user_id, role_name="admin")

        return self.list_user_roles(user_id=user_id)["roles"]

    def create_booking_request(self, payload: BookingRequestCreateIn) -> dict:
        response = (
            self.client.table("booking_requests")
            .insert(
                {
                    "requester_user_id": str(payload.requester_user_id),
                    "location": payload.location,
                    "date": payload.date.isoformat(),
                    "time_slot": payload.time_slot,
                    "purpose": payload.purpose,
                    "remarks": payload.remarks,
                    "status": BookingStatus.pending.value,
                }
            )
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create booking request",
            )
        return response.data[0]

    def list_booking_requests(self, status: BookingStatus | None = None) -> list[dict]:
        query = (
            self.client.table("booking_requests")
            .select("*")
            .order("created_at", desc=True)
        )
        if status:
            query = query.eq("status", status.value)
        response = query.execute()
        return response.data or []

    def decide_booking_request(
        self,
        request_id: UUID,
        payload: BookingRequestDecisionIn,
    ) -> dict:
        if payload.status not in {BookingStatus.accepted, BookingStatus.declined}:
            raise HTTPException(
                status_code=400,
                detail="Decision status must be accepted or declined",
            )

        update_payload: dict[str, str | None] = {
            "status": payload.status.value,
            "remarks": payload.remarks,
            "updated_at": datetime.now(UTC).isoformat(),
            "reviewed_at": datetime.now(UTC).isoformat(),
        }

        if payload.reviewer_user_id:
            update_payload["reviewed_by"] = str(payload.reviewer_user_id)

        response = (
            self.client.table("booking_requests")
            .update(update_payload)
            .eq("id", str(request_id))
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=404, detail="Booking request not found")
        return response.data[0]

    @staticmethod
    def _to_vector_literal(embedding: list[float]) -> str:
        return "[" + ",".join(str(value) for value in embedding) + "]"

    # ── Chat history CRUD ─────────────────────────────────────────────

    def create_chat_session(self, user_email: str, title: str = "New chat") -> dict:
        response = (
            self.client.table("chat_sessions")
            .insert({"user_email": user_email, "title": title})
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create chat session")
        return response.data[0]

    def list_chat_sessions(self, user_email: str) -> list[dict]:
        response = (
            self.client.table("chat_sessions")
            .select("*")
            .eq("user_email", user_email)
            .order("updated_at", desc=True)
            .execute()
        )
        return response.data or []

    def get_chat_messages(self, session_id: str) -> list[dict]:
        response = (
            self.client.table("chat_messages")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )
        return response.data or []

    def add_chat_message(self, session_id: str, role: str, content: str, metadata: dict | None = None) -> dict:
        response = (
            self.client.table("chat_messages")
            .insert({
                "session_id": session_id,
                "role": role,
                "content": content,
                "metadata": metadata or {},
            })
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to save message")
        # Bump session updated_at
        self.client.table("chat_sessions").update(
            {"updated_at": datetime.now(UTC).isoformat()}
        ).eq("id", session_id).execute()
        return response.data[0]

    def update_session_title(self, session_id: str, title: str) -> dict:
        response = (
            self.client.table("chat_sessions")
            .update({"title": title, "updated_at": datetime.now(UTC).isoformat()})
            .eq("id", session_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        return response.data[0]

    def update_chat_message_metadata(self, message_id: str, metadata: dict) -> dict:
        # First get existing metadata
        existing = self.client.table("chat_messages").select("metadata").eq("id", message_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Message not found")

        new_metadata = existing.data[0].get("metadata") or {}
        new_metadata.update(metadata)

        response = (
            self.client.table("chat_messages")
            .update({"metadata": new_metadata})
            .eq("id", message_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update message metadata")
        return response.data[0]
