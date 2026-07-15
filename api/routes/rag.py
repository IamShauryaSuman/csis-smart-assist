"""
RAG pipeline router — Client-Led Decentralized Sync.

Implements the O(1) memory footprint pattern: the frontend admin UI drives
the sync loop file-by-file, preventing OOM on 512MB free-tier hosts.

Flow:
1. GET /rag/delta → Backend scans Google Drive vs. DB, returns file delta
2. POST /rag/sync-file → Backend processes ONE file (extract, chunk, embed, store)
"""

from __future__ import annotations

import io
import logging
import re
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from core.config import get_settings
from core.database import get_supabase_client
from services.llm.hybrid import get_hybrid_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["rag"])

# Maximum chunk size in characters for text splitting
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


# ── Models ──────────────────────────────────────────────────────────────────


class FileDelta(BaseModel):
    gdrive_id: str
    name: str
    mime_type: str
    md5_checksum: str
    operation: str  # 'new', 'modified', 'deleted'


class DeltaResponse(BaseModel):
    new: list[FileDelta]
    modified: list[FileDelta]
    deleted: list[FileDelta]
    total_changes: int


class SyncResult(BaseModel):
    file_id: str
    gdrive_id: str
    name: str
    chunks_created: int
    status: str


class RagStatsResponse(BaseModel):
    total_files: int
    total_chunks: int
    files: list[dict[str, Any]]


# ── Auth Helper ─────────────────────────────────────────────────────────────


def _extract_user_id(authorization: str) -> str:
    """Validate JWT and extract user ID."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header.")
    token = authorization.removeprefix("Bearer ").strip()
    db = get_supabase_client()
    try:
        return db.auth.get_user(token).user.id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")


def _require_admin(user_id: str) -> None:
    """Verify admin privileges."""
    db = get_supabase_client()
    profile = (
        db.table("profiles").select("is_admin").eq("id", user_id).single().execute()
    )
    if not profile.data or not profile.data.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required.")


# ── Google Drive Helpers ────────────────────────────────────────────────────


def _get_drive_service() -> Any:
    """Build an authorized Google Drive API service."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    settings = get_settings()
    info = settings.google_service_account_info
    if not info:
        raise HTTPException(
            status_code=503, detail="Google Drive credentials not configured."
        )

    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def _list_drive_files() -> list[dict[str, str]]:
    """List all files in the configured Google Drive folder."""
    settings = get_settings()
    if not settings.google_drive_folder_id:
        return []

    service = _get_drive_service()
    files: list[dict[str, str]] = []
    page_token = None

    while True:
        response = (
            service.files()
            .list(
                q=f"'{settings.google_drive_folder_id}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType, md5Checksum)",
                pageToken=page_token,
                pageSize=100,
            )
            .execute()
        )

        for f in response.get("files", []):
            files.append({
                "gdrive_id": f["id"],
                "name": f["name"],
                "mime_type": f["mimeType"],
                "md5_checksum": f.get("md5Checksum", ""),
            })

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return files


def _download_file_content(gdrive_id: str, mime_type: str) -> str:
    """Download and extract text content from a Google Drive file.

    Supports Google Docs (export as plain text) and binary files
    (PDF text extraction via basic parsing).
    """
    service = _get_drive_service()

    # Google Docs/Sheets/Slides → export as plain text
    google_mime_exports = {
        "application/vnd.google-apps.document": "text/plain",
        "application/vnd.google-apps.spreadsheet": "text/csv",
        "application/vnd.google-apps.presentation": "text/plain",
    }

    if mime_type in google_mime_exports:
        request = service.files().export_media(
            fileId=gdrive_id, mimeType=google_mime_exports[mime_type]
        )
    else:
        request = service.files().get_media(fileId=gdrive_id)

    content_bytes = request.execute()

    if isinstance(content_bytes, bytes):
        if mime_type == "application/pdf":
            try:
                import PyPDF2
                from io import BytesIO
                reader = PyPDF2.PdfReader(BytesIO(content_bytes))
                text = ""
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\\n\\n"
                return text
            except Exception as e:
                import logging
                logging.getLogger(__name__).error("Failed to parse PDF", exc_info=True)
                return ""

        # Attempt UTF-8 decode for other raw formats
        try:
            return content_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return content_bytes.decode("latin-1", errors="ignore")

    return str(content_bytes)


# ── Text Chunking ───────────────────────────────────────────────────────────


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks for embedding.

    Uses paragraph-aware splitting to maintain context boundaries.
    """
    if not text.strip():
        return []

    # Split on double newlines (paragraphs) first
    paragraphs = re.split(r"\n{2,}", text.strip())
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        if current_length + len(paragraph) > chunk_size and current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(chunk_text)

            # Keep overlap: retain the last paragraph(s) up to overlap chars
            overlap_text = ""
            for p in reversed(current_chunk):
                if len(overlap_text) + len(p) <= overlap:
                    overlap_text = p + "\n\n" + overlap_text if overlap_text else p
                else:
                    break

            current_chunk = [overlap_text] if overlap_text else []
            current_length = len(overlap_text)

        current_chunk.append(paragraph)
        current_length += len(paragraph)

    # Don't forget the last chunk
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    # Handle very long paragraphs: split by sentences if chunk is still too large
    final_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) > chunk_size * 1.5:
            sentences = re.split(r"(?<=[.!?])\s+", chunk)
            sub_chunk = ""
            for sentence in sentences:
                if len(sub_chunk) + len(sentence) > chunk_size:
                    if sub_chunk:
                        final_chunks.append(sub_chunk.strip())
                    sub_chunk = sentence
                else:
                    sub_chunk += " " + sentence if sub_chunk else sentence
            if sub_chunk:
                final_chunks.append(sub_chunk.strip())
        else:
            final_chunks.append(chunk)

    return final_chunks


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/delta", response_model=DeltaResponse)
async def get_rag_delta(authorization: str = Header(...)):
    """Compare Google Drive state against the database and return the diff.

    Returns three sets: new files, modified files (checksum mismatch),
    and deleted files (in DB but not in Drive).
    """
    user_id = _extract_user_id(authorization)
    _require_admin(user_id)

    db = get_supabase_client()
    print("DB OBJECT IS:", db)
    # Get current DB state
    db_files = db.table("rag_files").select("gdrive_id, md5_checksum, name").execute()
    db_map: dict[str, dict] = {f["gdrive_id"]: f for f in (db_files.data or [])}

    # Get current Drive state
    drive_files = _list_drive_files()
    drive_map: dict[str, dict] = {f["gdrive_id"]: f for f in drive_files}

    new_files: list[FileDelta] = []
    modified_files: list[FileDelta] = []
    deleted_files: list[FileDelta] = []

    # Find new and modified files
    for gdrive_id, drive_file in drive_map.items():
        if gdrive_id not in db_map:
            new_files.append(FileDelta(**drive_file, operation="new"))
        elif drive_file["md5_checksum"] != db_map[gdrive_id]["md5_checksum"]:
            modified_files.append(FileDelta(**drive_file, operation="modified"))

    # Find deleted files
    for gdrive_id, db_file in db_map.items():
        if gdrive_id not in drive_map:
            deleted_files.append(
                FileDelta(
                    gdrive_id=gdrive_id,
                    name=db_file["name"],
                    mime_type="",
                    md5_checksum=db_file["md5_checksum"],
                    operation="deleted",
                )
            )

    total = len(new_files) + len(modified_files) + len(deleted_files)
    return DeltaResponse(
        new=new_files,
        modified=modified_files,
        deleted=deleted_files,
        total_changes=total,
    )


@router.post("/sync-file", response_model=SyncResult)
async def sync_single_file(
    gdrive_id: str = Query(..., description="Google Drive file ID to sync"),
    authorization: str = Header(...),
):
    """Process a single file: download, extract, chunk, embed, and store.

    Called by the frontend in a loop for each file in the delta,
    maintaining an O(1) memory footprint per request.
    """
    user_id = _extract_user_id(authorization)
    _require_admin(user_id)

    db = get_supabase_client()
    llm = get_hybrid_client()

    # Get file metadata from Drive
    drive_files = _list_drive_files()
    target_file = None
    for f in drive_files:
        if f["gdrive_id"] == gdrive_id:
            target_file = f
            break

    if not target_file:
        raise HTTPException(status_code=404, detail="File not found in Google Drive.")

    # Download and extract text content
    text_content = _download_file_content(gdrive_id, target_file["mime_type"])
    if not text_content.strip():
        return SyncResult(
            file_id="",
            gdrive_id=gdrive_id,
            name=target_file["name"],
            chunks_created=0,
            status="empty_file",
        )

    # Delete existing record if re-syncing a modified file
    existing = (
        db.table("rag_files")
        .select("id")
        .eq("gdrive_id", gdrive_id)
        .execute()
    )
    if existing.data:
        # CASCADE delete removes associated chunks automatically
        db.table("rag_files").delete().eq("gdrive_id", gdrive_id).execute()

    # Insert new file record
    file_record = (
        db.table("rag_files")
        .insert({
            "gdrive_id": target_file["gdrive_id"],
            "name": target_file["name"],
            "mime_type": target_file["mime_type"],
            "md5_checksum": target_file["md5_checksum"],
        })
        .execute()
    )
    file_id = file_record.data[0]["id"]

    # Chunk the text
    chunks = _chunk_text(text_content)

    # Embed and store each chunk
    chunks_created = 0
    for chunk_text in chunks:
        try:
            embedding = await llm.embed(chunk_text)
            db.table("rag_chunks").insert({
                "file_id": file_id,
                "content": chunk_text,
                "embedding": embedding,
            }).execute()
            chunks_created += 1
        except Exception:
            logger.exception(
                "Failed to embed chunk for file %s", target_file["name"]
            )

    logger.info(
        "Synced file '%s': %d chunks created", target_file["name"], chunks_created
    )

    return SyncResult(
        file_id=file_id,
        gdrive_id=gdrive_id,
        name=target_file["name"],
        chunks_created=chunks_created,
        status="synced",
    )


@router.delete("/file")
async def delete_rag_file(
    gdrive_id: str = Query(..., description="Google Drive file ID to remove"),
    authorization: str = Header(...),
):
    """Remove a file and all its chunks from the RAG index."""
    user_id = _extract_user_id(authorization)
    _require_admin(user_id)

    db = get_supabase_client()
    result = db.table("rag_files").delete().eq("gdrive_id", gdrive_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="File not found in RAG index.")

    return {"status": "deleted", "gdrive_id": gdrive_id}


@router.get("/stats", response_model=RagStatsResponse)
async def get_rag_stats(authorization: str = Header(...)):
    """Return RAG pipeline statistics: file count, chunk count, per-file details."""
    user_id = _extract_user_id(authorization)
    _require_admin(user_id)

    db = get_supabase_client()

    files = db.table("rag_files").select("id, name, mime_type, updated_at").execute()
    total_files = len(files.data) if files.data else 0

    # Count total chunks
    chunks = db.table("rag_chunks").select("id", count="exact").execute()
    total_chunks = chunks.count if hasattr(chunks, "count") and chunks.count else 0

    # Per-file chunk counts
    file_details: list[dict[str, Any]] = []
    for f in (files.data or []):
        chunk_count = (
            db.table("rag_chunks")
            .select("id", count="exact")
            .eq("file_id", f["id"])
            .execute()
        )
        file_details.append({
            "id": f["id"],
            "name": f["name"],
            "mime_type": f["mime_type"],
            "updated_at": f["updated_at"],
            "chunk_count": chunk_count.count if hasattr(chunk_count, "count") and chunk_count.count else 0,
        })

    return RagStatsResponse(
        total_files=total_files,
        total_chunks=total_chunks,
        files=file_details,
    )
