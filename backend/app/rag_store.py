from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import chromadb
except Exception:  # pragma: no cover
    chromadb = None


RAG_COLLECTION_NAME = "RAG_db"
RAG_DB_PATH = Path(__file__).resolve().parents[1] / "RAG_db"


def resolve_rag_db_path(db_path: str | Path | None = None) -> str:
    candidate = Path(db_path) if db_path else RAG_DB_PATH
    if candidate.is_absolute():
        return str(candidate)
    return str((Path(__file__).resolve().parents[1] / candidate).resolve())


_chroma_client = None


def get_rag_collection(
    db_path: str | Path | None = None,
    collection_name: str = RAG_COLLECTION_NAME,
):
    global _chroma_client
    if chromadb is None:
        raise RuntimeError("chromadb is not installed")

    os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
    
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=resolve_rag_db_path(db_path))
    
    return _chroma_client.get_or_create_collection(name=collection_name)


def get_source_metadata(
    collection,
    source_uri: str,
) -> dict[str, Any] | None:
    try:
        result = collection.get(
            where={"source_uri": source_uri}, include=["metadatas"])
    except Exception:
        return None

    metadatas = result.get("metadatas") or []
    if not metadatas or not metadatas[0]:
        return None
    return metadatas[0][0] or None


def replace_source_chunks(
    collection,
    *,
    source_uri: str,
    title: str,
    chunks: list[str],
    embeddings: list[list[float]],
    metadata: dict[str, Any] | None = None,
) -> int:
    collection.delete(where={"source_uri": source_uri})

    if not chunks:
        return 0

    rows = []
    base_metadata = metadata or {}
    for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
        rows.append(
            {
                "id": f"{source_uri}::{index}",
                "document": chunk,
                "embedding": embedding,
                "metadata": {
                    **base_metadata,
                    "source_uri": source_uri,
                    "title": title,
                    "chunk_index": index,
                },
            }
        )

    collection.add(
        ids=[row["id"] for row in rows],
        documents=[row["document"] for row in rows],
        embeddings=[row["embedding"] for row in rows],
        metadatas=[row["metadata"] for row in rows],
    )
    return len(rows)


def search_rag_collection(
    *,
    query_embedding: list[float],
    match_count: int = 5,
    db_path: str | Path | None = None,
    collection_name: str = RAG_COLLECTION_NAME,
) -> list[dict[str, Any]]:
    collection = get_rag_collection(
        db_path=db_path, collection_name=collection_name)
    if collection.count() == 0:
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=match_count,
    )

    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    ids = (results.get("ids") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    matches: list[dict[str, Any]] = []
    for index, document in enumerate(documents):
        metadata = metadatas[index] if index < len(metadatas) else {}
        metadata = metadata or {}
        distance = distances[index] if index < len(distances) else None
        matches.append(
            {
                "id": ids[index] if index < len(ids) else None,
                "document_id": metadata.get("source_uri"),
                "chunk_index": metadata.get("chunk_index", index),
                "content": document,
                "metadata": metadata,
                "similarity": round(1 - distance, 4) if distance is not None else None,
            }
        )

    return matches
