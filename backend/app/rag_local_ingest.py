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

import os as _os
_os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")

try:
    import chromadb
except Exception:  # pragma: no cover
    chromadb = None


def _get_embeddings(texts: list[str], use_gemini: bool = False, gemini_key: str = None, model_name: str = "nomic-embed-text", ollama_url: str = "http://localhost:11434") -> list[list[float]]:
    """Generate embeddings using either Gemini (cloud) or Ollama (local)."""
    if use_gemini and gemini_key:
        return _google_embed(texts, gemini_key)
    return _ollama_embed(texts, model_name, ollama_url)


def _google_embed(texts: list[str], api_key: str) -> list[list[float]]:
    """Generate 768-dim embeddings using Gemini."""
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=texts,
            task_type="retrieval_document",
            output_dimensionality=768,
        )
        return result["embeddings"]
    except Exception as exc:
        print(f"[Gemini Embed] Failed: {exc}. Falling back to Ollama.")
        return _ollama_embed(texts)


def _ollama_embed(texts: list[str], model_name: str = "nomic-embed-text", ollama_url: str = "http://localhost:11434") -> list[list[float]]:
    """Generate embeddings using Ollama's embedding API."""
    import requests

    embeddings = []
    # Batch in groups of 10 to avoid overwhelming Ollama
    batch_size = 10
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            response = requests.post(
                f"{ollama_url}/api/embed",
                json={"model": model_name, "input": batch},
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            batch_embeddings = data.get("embeddings", [])
            embeddings.extend(batch_embeddings)
        except Exception as exc:
            print(f"[Ollama Embed] Batch {i//batch_size} failed: {exc}")
            # Return zero vectors as fallback
            dim = 768
            embeddings.extend([[0.0] * dim for _ in batch])
    return embeddings


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


def sync_local_rag_to_chromadb(
    data_dir: str,
    collection_name: str = "RAG_db",
    db_path: str = "./RAG_db",
    chunk_size: int = 140,
    overlap: int = 30,
    embedding_model: str = "nomic-embed-text",
) -> dict[str, Any]:
    """Ingest local documents into ChromaDB with Ollama embeddings.

    Uses Ollama's embedding API for embeddings.
    """
    summary: dict[str, Any] = {
        "data_dir": data_dir,
        "processed_files": 0,
        "chunks_stored": 0,
        "skipped_unsupported": 0,
        "errors": [],
    }

    if chromadb is None:
        summary["errors"].append("chromadb is not installed")
        return summary

    base_path = _resolve_data_dir(data_dir)
    if not base_path.exists() or not base_path.is_dir():
        summary["errors"].append(f"Data directory not found: {base_path}")
        return summary

    from .rag_store import get_rag_collection
    try:
        collection = get_rag_collection(db_path=db_path, collection_name=collection_name)
    except Exception as exc:
        summary["errors"].append(f"Failed to get ChromaDB collection: {exc}")
        return summary

    # Check if existing embeddings are zero-vectors (broken previous ingestion)
    if collection.count() > 0:
        try:
            sample = collection.peek(limit=1)
            sample_emb = (sample.get("embeddings") or [[]])[0]
            if sample_emb and all(v == 0.0 for v in sample_emb):
                print("[RAG ChromaDB] Detected zero-vector embeddings — clearing collection for re-ingestion")
                # Delete all existing chunks
                all_ids = collection.get()["ids"]
                if all_ids:
                    collection.delete(ids=all_ids)
        except Exception as exc:
            print(f"[RAG ChromaDB] Error checking embeddings: {exc}")

    all_chunks: list[str] = []
    all_ids: list[str] = []
    chunk_counter = 0

    for path in sorted(base_path.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            summary["skipped_unsupported"] += 1
            continue

        summary["processed_files"] += 1
        try:
            raw = path.read_bytes()
            text = _extract_text(raw, _infer_mime_type(path))
            if not text.strip():
                summary["errors"].append(f"No text extracted from {path.name}")
                continue

            chunks = _chunk_text(text, chunk_size=chunk_size, overlap=overlap)
            for chunk in chunks:
                all_chunks.append(chunk)
                all_ids.append(f"chunk_{chunk_counter}")
                chunk_counter += 1
        except Exception as exc:
            summary["errors"].append(f"{path.name}: {exc}")

    if all_chunks:
        try:
            from .config import get_settings
            settings = get_settings()
            embeddings = _get_embeddings(
                texts=all_chunks,
                use_gemini=settings.use_gemini,
                gemini_key=settings.gemini_api_key,
                model_name=embedding_model,
                ollama_url=settings.ollama_base_url
            )
        except Exception as exc:
            summary["errors"].append(f"Embedding failed: {exc}")
            return summary
        collection.upsert(
            embeddings=embeddings,
            documents=all_chunks,
            ids=all_ids,
        )
        summary["chunks_stored"] = len(all_chunks)

    return summary
from .google_client import get_google_drive_client


def sync_google_drive_rag_data(
    service: SupabaseService,
    folder_id: str,
    vector_dimensions: int,
    embedding_model: str = "nomic-embed-text",
    db_path: str = "./RAG_db",
) -> dict[str, Any]:
    """Sync documents from a Google Drive folder to Supabase and ChromaDB."""
    from .config import get_settings
    settings = get_settings()

    summary: dict[str, Any] = {
        "folder_id": folder_id,
        "processed_files": 0,
        "ingested_files": 0,
        "chunks_written": 0,
        "errors": [],
    }

    try:
        drive_service = get_google_drive_client(settings)
    except Exception as exc:
        summary["errors"].append(f"Failed to initialize Drive client: {exc}")
        return summary

    try:
        # List files in the folder
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

    # Initialize ChromaDB
    from .rag_store import get_rag_collection
    try:
        collection = get_rag_collection(db_path=db_path, collection_name="RAG_db")
    except Exception as exc:
        summary["errors"].append(f"Failed to get ChromaDB collection: {exc}")
        return summary


    default_embedding = [0.0] * vector_dimensions

    for file in files:
        file_id = file["id"]
        file_name = file["name"]
        mime_type = file["mimeType"]
        content_hash = file.get("md5Checksum", file_id)

        # Check extension/mime
        is_supported = False
        for ext in SUPPORTED_EXTENSIONS:
            if file_name.lower().endswith(ext):
                is_supported = True
                break
        
        if not is_supported and "text" not in mime_type and "pdf" not in mime_type and "document" not in mime_type:
            continue

        summary["processed_files"] += 1
        try:
            source_uri = f"gdrive://{file_id}"

            # Check if already ingested in Supabase
            existing = (
                service.client.table("rag_documents")
                .select("id,metadata")
                .eq("source_uri", source_uri)
                .limit(1)
                .execute()
            )
            existing_row = existing.data[0] if existing.data else None
            existing_hash = ((existing_row or {}).get("metadata") or {}).get("content_hash")

            # We'll skip if hash matches (optional optimization)
            # if existing_hash == content_hash:
            #     continue

            # Download file
            if "google-apps.document" in mime_type:
                # Export Google Docs as PDF
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

            # Sync to Supabase
            document = service.upsert_rag_document_by_source(
                title=file_name,
                source_uri=source_uri,
                metadata={
                    "ingest_source": "google_drive",
                    "file_id": file_id,
                    "content_hash": content_hash,
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )

            written = service.replace_rag_chunks_for_document(
                document_id=document["id"],
                chunks=chunks,
                embedding=default_embedding,
                metadata={
                    "file_id": file_id,
                    "ingest_source": "google_drive",
                },
            )

            # Sync to ChromaDB
            # (In a real app, we'd use better embeddings, but using _local_embed for consistency)
            try:
                from .config import get_settings
                settings = get_settings()
                embeddings = _get_embeddings(
                    texts=chunks,
                    use_gemini=settings.use_gemini,
                    gemini_key=settings.gemini_api_key,
                    model_name=embedding_model,
                    ollama_url=settings.ollama_base_url
                )
                # For Chroma, we use source_uri as prefix for IDs
                ids = [f"{source_uri}::{i}" for i in range(len(chunks))]
                
                # Clear old chunks for this source in Chroma
                collection.delete(where={"source_uri": source_uri})
                
                collection.add(
                    embeddings=embeddings,
                    documents=chunks,
                    ids=ids,
                    metadatas=[{
                        "source_uri": source_uri,
                        "title": file_name,
                        "chunk_index": i,
                        "ingest_source": "google_drive"
                    } for i in range(len(chunks))]
                )
            except Exception as exc:
                summary["errors"].append(f"ChromaDB sync failed for {file_name}: {exc}")

            summary["ingested_files"] += 1
            summary["chunks_written"] += written
        except Exception as exc:
            summary["errors"].append(f"{file_name}: {exc}")

    return summary
