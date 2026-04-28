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

import os as _os
_os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")

try:
    import chromadb
except Exception:  # pragma: no cover
    chromadb = None


def _get_embeddings(texts: list[str], gemini_key: str | None = None) -> list[list[float]]:
    """Generate embeddings using Gemini."""
    return _google_embed(texts, gemini_key)


def _google_embed(texts: list[str], api_key: str | None) -> list[list[float]]:
    """Generate 768-dim embeddings using Gemini."""
    if not api_key:
        print("[Gemini Embed] Missing GEMINI_API_KEY")
        return [[0.0] * 768 for _ in texts]

    import google.generativeai as genai
    genai.configure(api_key=api_key)

    def _extract_vector(result: Any) -> list[float]:
        embedding = result.get("embedding")
        if isinstance(embedding, list) and embedding:
            if len(embedding) == 768 and all(isinstance(value, (int, float)) for value in embedding):
                return [float(value) for value in embedding]
            if isinstance(embedding[0], list) and embedding[0]:
                return [float(value) for value in embedding[0]]
            if isinstance(embedding[0], (int, float)):
                return [float(value) for value in embedding]

        embeddings = result.get("embeddings")
        if isinstance(embeddings, list) and embeddings:
            first = embeddings[0]
            if isinstance(first, dict) and isinstance(first.get("embedding"), list):
                return [float(value) for value in first["embedding"]]
            if isinstance(first, list) and first:
                if isinstance(first[0], list) and first[0]:
                    return [float(value) for value in first[0]]
                if isinstance(first[0], (int, float)):
                    return [float(value) for value in first]

        raise ValueError(f"Unexpected Gemini embedding response shape: {result}")

    try:
        embeddings: list[list[float]] = []
        for text in texts:
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=text,
                task_type="retrieval_document",
                output_dimensionality=768,
            )
            embeddings.append(_extract_vector(result))
        return embeddings
    except Exception as exc:
        print(f"[Gemini Embed] Failed: {exc}")
        return [[0.0] * 768 for _ in texts]


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


def _chunk_text(text: str, chunk_size: int = 300, overlap: int = 60) -> list[str]:
    words = text.split()
    if not words:
        return []

    # Detect header: take the first line(s) up to a reasonable length as context prefix.
    # This ensures tabular data always has column headers in every chunk.
    lines = text.split("\n")
    header_lines: list[str] = []
    header_word_count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        line_words = stripped.split()
        # Stop collecting header once we've got enough context or hit data rows
        if header_word_count + len(line_words) > 60:
            break
        header_lines.append(stripped)
        header_word_count += len(line_words)
        # If we found column-like headers (multiple short fields), stop
        if header_word_count >= 15:
            break

    header_prefix = " | ".join(header_lines).strip()

    step = max(chunk_size - overlap, 1)
    chunks: list[str] = []
    for index in range(0, len(words), step):
        segment = words[index:index + chunk_size]
        if not segment:
            continue
        chunk_text = " ".join(segment).strip()
        # Prepend header to non-first chunks so they have column context
        if index > 0 and header_prefix:
            chunk_text = f"[Context: {header_prefix}]\n{chunk_text}"
        chunks.append(chunk_text)
        if index + chunk_size >= len(words):
            break
    return chunks


def _file_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


from .google_client import get_google_drive_client


def sync_google_drive_rag_data(
    folder_id: str,
    gemini_key: str | None = None,
    db_path: str = "./RAG_db",
) -> dict[str, Any]:
    """Sync documents from a Google Drive folder directly into ChromaDB.

    No Supabase involvement — all state is stored in ChromaDB only.
    Every call is a full re-sync: old chunks for each source are deleted
    before new ones are written.
    """
    from .config import get_settings
    from .rag_store import get_rag_collection

    settings = get_settings()

    summary: dict[str, Any] = {
        "folder_id": folder_id,
        "processed": 0,
        "ingested": 0,
        "chunks_written": 0,
        "errors": [],
    }

    # ── Drive client ───────────────────────────────────────────────────
    try:
        drive_service = get_google_drive_client(settings)
    except Exception as exc:
        summary["errors"].append(f"Failed to initialize Drive client: {exc}")
        return summary

    # ── List files ─────────────────────────────────────────────────────
    try:
        query = f"'{folder_id}' in parents and trashed = false"
        results = drive_service.files().list(
            q=query, fields="files(id, name, mimeType, md5Checksum)"
        ).execute()
        files = results.get("files", [])
    except Exception as exc:
        summary["errors"].append(f"Failed to list files from Drive: {exc}")
        return summary

    if not files:
        summary["errors"].append(f"No files found in Drive folder: {folder_id}")
        return summary

    # ── ChromaDB collection ────────────────────────────────────────────
    try:
        collection = get_rag_collection(db_path=db_path, collection_name="RAG_db")
    except Exception as exc:
        summary["errors"].append(f"Failed to get ChromaDB collection: {exc}")
        return summary

    # ── Per-file ingestion ─────────────────────────────────────────────
    for file in files:
        file_id = file["id"]
        file_name = file["name"]
        mime_type = file["mimeType"]

        # Filter by supported type
        is_supported = any(file_name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS)
        if not is_supported and "text" not in mime_type and "pdf" not in mime_type and "document" not in mime_type:
            continue

        summary["processed"] += 1
        source_uri = f"gdrive://{file_id}"

        try:
            # Download / export
            if "google-apps.document" in mime_type:
                raw = drive_service.files().export(
                    fileId=file_id, mimeType="application/pdf"
                ).execute()
                mime_type = "application/pdf"
            else:
                raw = drive_service.files().get_media(fileId=file_id).execute()

            text = _extract_text(raw, mime_type)
            if not text.strip():
                summary["errors"].append(f"No text extracted from {file_name}")
                continue

            chunks = _chunk_text(text)
            if not chunks:
                summary["errors"].append(f"No chunks created from {file_name}")
                continue

            # Generate embeddings
            embeddings = _get_embeddings(
                texts=chunks,
                gemini_key=gemini_key or settings.gemini_api_key,
            )

            # Replace old chunks for this source in ChromaDB
            try:
                collection.delete(where={"source_uri": source_uri})
            except Exception:
                pass  # collection may be empty; ignore

            ids = [f"{source_uri}::{i}" for i in range(len(chunks))]
            collection.add(
                embeddings=embeddings,
                documents=chunks,
                ids=ids,
                metadatas=[{
                    "source_uri": source_uri,
                    "title": file_name,
                    "chunk_index": i,
                    "ingest_source": "google_drive",
                } for i in range(len(chunks))],
            )

            summary["ingested"] += 1
            summary["chunks_written"] += len(chunks)

        except Exception as exc:
            summary["errors"].append(f"{file_name}: {exc}")

    return summary
