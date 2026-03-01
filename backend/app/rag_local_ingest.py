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
    import PyPDF2
except Exception:  # pragma: no cover
    PyPDF2 = None

from .services import SupabaseService

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".html", ".htm", ".txt", ".md"}


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
        if PyPDF2 is None:
            return ""
        reader = PyPDF2.PdfReader(io.BytesIO(raw))
        extracted = "\n".join((page.extract_text() or "")
                              for page in reader.pages)
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


def sync_local_rag_data_folder(
    service: SupabaseService,
    data_dir: str,
    vector_dimensions: int,
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

    default_embedding = [0.0] * vector_dimensions

    for path in sorted(base_path.rglob("*")):
        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            summary["skipped_unsupported"] += 1
            continue

        summary["processed_files"] += 1
        try:
            raw = path.read_bytes()
            content_hash = _file_hash(raw)
            relative_path = path.relative_to(base_path).as_posix()
            source_uri = f"local://data/{relative_path}"

            existing = (
                service.client.table("rag_documents")
                .select("id,metadata")
                .eq("source_uri", source_uri)
                .limit(1)
                .execute()
            )
            existing_row = existing.data[0] if existing.data else None
            existing_hash = ((existing_row or {}).get(
                "metadata") or {}).get("content_hash")

            if existing_hash == content_hash:
                summary["skipped_unchanged"] += 1
                continue

            text = _extract_text(raw, _infer_mime_type(path))
            if not text.strip():
                summary["errors"].append(
                    f"No text extracted from {relative_path}")
                continue

            chunks = _chunk_text(text)
            if not chunks:
                summary["errors"].append(
                    f"No chunks created from {relative_path}")
                continue

            document = service.upsert_rag_document_by_source(
                title=path.name,
                source_uri=source_uri,
                metadata={
                    "ingest_source": "local_data_folder",
                    "relative_path": relative_path,
                    "content_hash": content_hash,
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )

            written = service.replace_rag_chunks_for_document(
                document_id=document["id"],
                chunks=chunks,
                embedding=default_embedding,
                metadata={
                    "relative_path": relative_path,
                    "ingest_source": "local_data_folder",
                },
            )

            summary["ingested_files"] += 1
            summary["chunks_written"] += written
        except Exception as exc:
            summary["errors"].append(f"{path.name}: {exc}")

    return summary
