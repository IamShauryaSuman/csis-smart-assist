from datetime import UTC, datetime
from uuid import UUID

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
        response = (
            self.client.table("app_users")
            .upsert(
                {
                    "id": str(payload.id),
                    "email": payload.email,
                    "full_name": payload.full_name,
                },
                on_conflict="id",
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

    @staticmethod
    def _to_vector_literal(embedding: list[float]) -> str:
        return "[" + ",".join(str(value) for value in embedding) + "]"
