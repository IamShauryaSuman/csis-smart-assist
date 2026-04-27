from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import io
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
try:
    import docx
except Exception:  # pragma: no cover
    docx = None

try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
except Exception:  # pragma: no cover
    pdfminer_extract_text = None

try:
    import PyPDF2
except Exception:  # pragma: no cover
    PyPDF2 = None

from googleapiclient.discovery import Resource
from googleapiclient.http import MediaIoBaseDownload

from .rag_store import get_rag_collection
from .rag_store import get_source_metadata
from .rag_store import replace_source_chunks

import os as _os
_os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")

try:
    import chromadb
except Exception:  # pragma: no cover
    chromadb = None


def _gemini_embed(texts: list[str], api_key: str) -> list[list[float]]:
    """Generate embeddings using Gemini's text-embedding-004 model.

    This replaces the local SentenceTransformer model to stay within
    Render free-tier memory limits (512 MB).
    """
    from google import genai

    client = genai.Client(api_key=api_key)
    # Batch in groups of 100 to respect API limits
    all_embeddings: list[list[float]] = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=batch,
        )
        for emb in result.embeddings:
            all_embeddings.append(emb.values)
    return all_embeddings


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".html", ".htm", ".txt", ".md"}
SUPPORTED_DRIVE_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/html",
    "text/plain",
    "text/markdown",
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
}


def _infer_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "application/pdf"
    if suffix == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if suffix in {".html", ".htm"}:
        return "text/html"
    if suffix == ".md":
        return "text/markdown"
    return "text/plain"


def _extract_text(raw: bytes, mime_type: str) -> str:
    extracted = ""
    if "pdf" in mime_type:
        if PyPDF2 is not None:
            try:
                reader = PyPDF2.PdfReader(io.BytesIO(raw), strict=False)
                extracted = "\n".join(
                    (page.extract_text() or "") for page in reader.pages
                )
            except Exception:
                extracted = ""

        if not extracted.strip() and pdfminer_extract_text is not None:
            try:
                extracted = pdfminer_extract_text(io.BytesIO(raw)) or ""
            except Exception:
                extracted = ""
    elif "word" in mime_type or "document" in mime_type:
        if docx is None:
            return ""
        document = docx.Document(io.BytesIO(raw))
        extracted = "\n".join(para.text for para in document.paragraphs)
    elif "html" in mime_type:
        soup = BeautifulSoup(raw, "html.parser")
        for anchor in soup.find_all("a", href=True):
            text = anchor.get_text(strip=True)
            href = anchor["href"]
            if text and href and not href.startswith("#") and not href.startswith("javascript:"):
                anchor.replace_with(f"{text} (URL: {href})")
        extracted = soup.get_text(separator=" ", strip=True)
    else:
        extracted = raw.decode("utf-8", errors="ignore")
    return extracted.strip()


def _extract_drive_text(raw: bytes, mime_type: str, fallback_name: str) -> str:
    normalized_mime = mime_type.lower()
    if normalized_mime == "application/vnd.google-apps.spreadsheet":
        normalized_mime = "text/plain"
    if normalized_mime == "application/vnd.google-apps.presentation":
        normalized_mime = "application/pdf"

    if normalized_mime in {"text/plain", "text/markdown", "text/csv"}:
        normalized_mime = "text/plain"
    elif normalized_mime in {"text/html"}:
        normalized_mime = "text/html"
    elif normalized_mime in {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }:
        pass
    else:
        suffix = Path(fallback_name).suffix.lower()
        normalized_mime = _infer_mime_type(Path(f"unknown{suffix}"))

    return _extract_text(raw=raw, mime_type=normalized_mime)


def _chunk_text(text: str, chunk_size: int = 140, overlap: int = 30) -> list[str]:
    words = text.split()
    if not words:
        return []

    step = max(chunk_size - overlap, 1)
    chunks: list[str] = []
    for index in range(0, len(words), step):
        segment = words[index:index + chunk_size]
        if not segment:
            continue
        chunks.append(" ".join(segment).strip())
        if index + chunk_size >= len(words):
            break
    return chunks


def _file_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _resolve_data_dir(data_dir: str) -> Path:
    candidate = Path(data_dir)
    if candidate.is_absolute():
        return candidate

    backend_root = Path(__file__).resolve().parents[1]
    return (backend_root / candidate).resolve()


def _store_text_source(
    *,
    collection,
    source_uri: str,
    title: str,
    text: str,
    raw: bytes,
    gemini_api_key: str,
    metadata: dict[str, Any],
    chunk_size: int = 140,
    overlap: int = 30,
) -> int:
    content_hash = _file_hash(raw)
    existing_metadata = get_source_metadata(collection, source_uri)
    if (existing_metadata or {}).get("content_hash") == content_hash:
        return 0

    if not text.strip():
        raise ValueError("No text extracted")

    chunks = _chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    if not chunks:
        raise ValueError("No chunks created")

    embeddings = _gemini_embed(chunks, gemini_api_key)

    return replace_source_chunks(
        collection,
        source_uri=source_uri,
        title=title,
        chunks=chunks,
        embeddings=embeddings,
        metadata={
            **metadata,
            "content_hash": content_hash,
            "updated_at": datetime.now(UTC).isoformat(),
        },
    )


def _drive_export_mime_type(file_mime_type: str) -> str | None:
    if file_mime_type == "application/vnd.google-apps.document":
        return "text/plain"
    if file_mime_type == "application/vnd.google-apps.spreadsheet":
        return "text/csv"
    if file_mime_type == "application/vnd.google-apps.presentation":
        return "application/pdf"
    return None


def _download_drive_file(
    drive_service: Resource,
    file_id: str,
    file_mime_type: str,
) -> bytes:
    export_mime = _drive_export_mime_type(file_mime_type)
    if export_mime:
        request = drive_service.files().export_media(
            fileId=file_id,
            mimeType=export_mime,
        )
    else:
        request = drive_service.files().get_media(fileId=file_id)

    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    return buffer.getvalue()


def _list_drive_files(
    drive_service: Resource,
    folder_id: str,
    recursive: bool,
    max_files: int,
) -> list[dict[str, Any]]:
    queue = [folder_id]
    seen_folders: set[str] = set()
    files: list[dict[str, Any]] = []

    while queue and len(files) < max_files:
        current_folder_id = queue.pop(0)
        if current_folder_id in seen_folders:
            continue
        seen_folders.add(current_folder_id)

        page_token = None
        while len(files) < max_files:
            response = (
                drive_service.files()
                .list(
                    q=f"'{current_folder_id}' in parents and trashed = false",
                    fields=(
                        "nextPageToken,"
                        "files(id,name,mimeType,modifiedTime,md5Checksum,parents)"
                    ),
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    pageToken=page_token,
                    pageSize=200,
                )
                .execute()
            )

            for item in response.get("files", []):
                item_mime = item.get("mimeType", "")
                if item_mime == "application/vnd.google-apps.folder":
                    if recursive:
                        queue.append(item["id"])
                    continue

                if item_mime not in SUPPORTED_DRIVE_MIME_TYPES:
                    continue

                files.append(item)
                if len(files) >= max_files:
                    break

            page_token = response.get("nextPageToken")
            if not page_token:
                break

    return files


def sync_local_rag_data_folder(
    data_dir: str,
    vector_dimensions: int,
    gemini_api_key: str | None = None,
    chunk_size: int = 140,
    overlap: int = 30,
) -> dict[str, Any]:
    base_path = _resolve_data_dir(data_dir)
    summary: dict[str, Any] = {
        "data_dir": str(base_path),
        "processed_files": 0,
        "ingested_files": 0,
        "skipped_unchanged": 0,
        "skipped_unsupported": 0,
        "chunks_written": 0,
        "errors": [],
    }

    if not base_path.exists() or not base_path.is_dir():
        summary["errors"].append(f"Data directory not found: {base_path}")
        return summary

    if not gemini_api_key:
        summary["errors"].append(
            "GEMINI_API_KEY not set; skipping RAG ingestion")
        return summary

    collection = get_rag_collection()

    for path in sorted(base_path.rglob("*")):
        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            summary["skipped_unsupported"] += 1
            continue

        summary["processed_files"] += 1
        try:
            raw = path.read_bytes()
            relative_path = path.relative_to(base_path).as_posix()
            source_uri = f"local://data/{relative_path}"
            text = _extract_text(raw, _infer_mime_type(path))
            written = _store_text_source(
                collection=collection,
                source_uri=source_uri,
                title=path.name,
                text=text,
                raw=raw,
                gemini_api_key=gemini_api_key,
                metadata={
                    "ingest_source": "local_data_folder",
                    "relative_path": relative_path,
                },
                chunk_size=chunk_size,
                overlap=overlap,
            )
            if written == 0:
                summary["skipped_unchanged"] += 1
            else:
                summary["ingested_files"] += 1
                summary["chunks_written"] += written
        except Exception as exc:
            summary["errors"].append(f"{path.name}: {exc}")

    return summary


def sync_local_rag_to_chromadb(
    data_dir: str,
    collection_name: str = "RAG_db",
    db_path: str = "./RAG_db",
    chunk_size: int = 140,
    overlap: int = 30,
    gemini_api_key: str | None = None,
) -> dict[str, Any]:
    raise NotImplementedError(
        "Local data folder ingestion has been removed; use Google Drive ingestion instead.")


def sync_google_drive_rag_folder(
    drive_service: Resource,
    folder_id: str,
    vector_dimensions: int,
    recursive: bool = True,
    max_files: int = 500,
    gemini_api_key: str | None = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "folder_id": folder_id,
        "processed_files": 0,
        "ingested_files": 0,
        "skipped_unchanged": 0,
        "skipped_unsupported": 0,
        "chunks_written": 0,
        "errors": [],
    }

    if not folder_id.strip():
        summary["errors"].append("Google Drive folder_id is empty")
        return summary

    if not gemini_api_key:
        summary["errors"].append(
            "GEMINI_API_KEY not set; skipping RAG ingestion")
        return summary

    collection = get_rag_collection()

    try:
        drive_files = _list_drive_files(
            drive_service=drive_service,
            folder_id=folder_id,
            recursive=recursive,
            max_files=max_files,
        )
    except Exception as exc:
        summary["errors"].append(f"Failed to list Drive files: {exc}")
        return summary

    for drive_file in drive_files:
        summary["processed_files"] += 1
        file_id = str(drive_file.get("id"))
        file_name = str(drive_file.get("name") or file_id)
        file_mime_type = str(drive_file.get("mimeType") or "")
        modified_time = str(drive_file.get("modifiedTime") or "")
        source_uri = f"gdrive://{file_id}"

        if file_mime_type not in SUPPORTED_DRIVE_MIME_TYPES:
            summary["skipped_unsupported"] += 1
            continue

        try:
            raw = _download_drive_file(
                drive_service=drive_service,
                file_id=file_id,
                file_mime_type=file_mime_type,
            )
            text = _extract_drive_text(
                raw=raw,
                mime_type=file_mime_type,
                fallback_name=file_name,
            )
            written = _store_text_source(
                collection=collection,
                source_uri=source_uri,
                title=file_name,
                text=text,
                raw=raw,
                gemini_api_key=gemini_api_key,
                metadata={
                    "ingest_source": "google_drive",
                    "google_drive_file_id": file_id,
                    "google_drive_mime_type": file_mime_type,
                    "google_drive_modified_time": modified_time,
                },
            )

            if written == 0:
                summary["skipped_unchanged"] += 1
            else:
                summary["ingested_files"] += 1
                summary["chunks_written"] += written
        except Exception as exc:
            summary["errors"].append(f"{file_name}: {exc}")

    return summary
