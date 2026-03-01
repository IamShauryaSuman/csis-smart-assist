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
    RagChunkCreateIn,
    RagDocumentCreateIn,
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
                    "resource": payload.resource,
                    "date": payload.date.isoformat(),
                    "time_slot": payload.time_slot,
                    "purpose": payload.purpose,
                    "participants": payload.participants,
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

    def create_rag_document(self, payload: RagDocumentCreateIn) -> dict:
        response = (
            self.client.table("rag_documents")
            .insert(
                {
                    "title": payload.title,
                    "source_uri": payload.source_uri,
                    "metadata": payload.metadata,
                }
            )
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=500, detail="Failed to create document")
        return response.data[0]

    def upsert_rag_document_by_source(
        self,
        title: str,
        source_uri: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        response = (
            self.client.table("rag_documents")
            .select("id,title,source_uri,metadata")
            .eq("source_uri", source_uri)
            .limit(1)
            .execute()
        )

        payload = {
            "title": title,
            "source_uri": source_uri,
            "metadata": metadata or {},
        }

        if response.data:
            updated = (
                self.client.table("rag_documents")
                .update(payload)
                .eq("id", response.data[0]["id"])
                .execute()
            )
            if not updated.data:
                raise HTTPException(
                    status_code=500, detail="Failed to update document")
            return updated.data[0]

        created = self.client.table("rag_documents").insert(payload).execute()
        if not created.data:
            raise HTTPException(
                status_code=500, detail="Failed to create document")
        return created.data[0]

    def replace_rag_chunks_for_document(
        self,
        document_id: UUID | str,
        chunks: list[str],
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> int:
        if len(embedding) != self.vector_dimensions:
            raise HTTPException(
                status_code=400,
                detail=f"Embedding must have {self.vector_dimensions} dimensions",
            )

        self.client.table("rag_chunks").delete().eq(
            "document_id", str(document_id)).execute()

        if not chunks:
            return 0

        embedding_literal = self._to_vector_literal(embedding)
        rows = [
            {
                "document_id": str(document_id),
                "chunk_index": index,
                "content": content,
                "embedding": embedding_literal,
                "metadata": metadata or {},
            }
            for index, content in enumerate(chunks)
        ]

        inserted_total = 0
        batch_size = 200
        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]
            inserted = self.client.table("rag_chunks").insert(batch).execute()
            inserted_total += len(inserted.data or [])

        return inserted_total

    def create_rag_chunk(self, payload: RagChunkCreateIn) -> dict:
        if len(payload.embedding) != self.vector_dimensions:
            raise HTTPException(
                status_code=400,
                detail=f"Embedding must have {self.vector_dimensions} dimensions",
            )

        embedding_literal = self._to_vector_literal(payload.embedding)
        response = (
            self.client.table("rag_chunks")
            .insert(
                {
                    "document_id": str(payload.document_id),
                    "chunk_index": payload.chunk_index,
                    "content": payload.content,
                    "embedding": embedding_literal,
                    "metadata": payload.metadata,
                }
            )
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=500, detail="Failed to create chunk")
        return response.data[0]

    def search_rag_chunks(self, payload: RagSearchIn) -> list[dict]:
        if len(payload.embedding) != self.vector_dimensions:
            raise HTTPException(
                status_code=400,
                detail=f"Embedding must have {self.vector_dimensions} dimensions",
            )

        response = self.client.rpc(
            "match_rag_chunks",
            {
                "query_embedding": self._to_vector_literal(payload.embedding),
                "match_count": payload.match_count,
            },
        ).execute()
        return response.data or []

    def search_rag_chunks_from_embedding(
        self,
        embedding: list[float],
        match_count: int = 5,
    ) -> list[dict]:
        if len(embedding) != self.vector_dimensions:
            raise HTTPException(
                status_code=400,
                detail=f"Embedding must have {self.vector_dimensions} dimensions",
            )

        response = self.client.rpc(
            "match_rag_chunks",
            {
                "query_embedding": self._to_vector_literal(embedding),
                "match_count": match_count,
            },
        ).execute()
        return response.data or []

    def search_rag_chunks_by_text(
        self,
        query: str,
        match_count: int = 5,
    ) -> list[dict]:
        normalized = query.strip()
        if not normalized:
            return []

        try:
            direct = (
                self.client.table("rag_chunks")
                .select("id,document_id,chunk_index,content,metadata")
                .ilike("content", f"%{normalized}%")
                .limit(match_count)
                .execute()
            )
            if direct.data:
                return direct.data

            tokens = [
                token
                for token in re.findall(r"[a-zA-Z0-9]+", normalized.lower())
                if len(token) > 2
            ][:6]
            if not tokens:
                return []

            or_filter = ",".join(
                f"content.ilike.%{token}%" for token in tokens
            )
            token_match = (
                self.client.table("rag_chunks")
                .select("id,document_id,chunk_index,content,metadata")
                .or_(or_filter)
                .limit(match_count)
                .execute()
            )
            return token_match.data or []
        except Exception:
            return []

    @staticmethod
    def _to_vector_literal(embedding: list[float]) -> str:
        return "[" + ",".join(str(value) for value in embedding) + "]"
