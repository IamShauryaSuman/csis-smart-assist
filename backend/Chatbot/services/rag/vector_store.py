import os
import uuid
import chromadb
from sentence_transformers import SentenceTransformer
import transformers
transformers.logging.set_verbosity_error()

# Initialize models
embed_model = SentenceTransformer("intfloat/e5-base-v2")
client = chromadb.PersistentClient(path="./RAG_db")

def chunk_text(text: str, chunk_size=30):
    chunks = []
    current_chunk = ""
    words = text.split()
    for word in words:
        current_chunk += word + " "
        if len(current_chunk.split()) >= chunk_size:
            chunks.append(current_chunk.strip())
            current_chunk = ""
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks

def embed(chunks):
    """Embed chunks using sentence transformers."""
    if not chunks:
        return []
    embeddings = embed_model.encode(chunks, show_progress_bar=False)
    return embeddings

def create_vector_store(embeddings, chunks, collection_name="RAG_db"):
    """Adds documents to ChromaDB."""
    if not chunks:
        return None
    collection = client.get_or_create_collection(name=collection_name)
    ids = [f"chunk_{uuid.uuid4().hex}" for _ in range(len(chunks))]
    
    collection.add(
        embeddings=embeddings.tolist() if hasattr(embeddings, 'tolist') else embeddings,
        documents=chunks,
        ids=ids
    )
    return collection

def retrieve_relevant_chunks(query: str, collection_name="RAG_db", top_k=20):
    """Retrieves top_k chunks relevant to the query."""
    collection = client.get_or_create_collection(name=collection_name)
    if collection.count() == 0:
        return []
    
    query_embedding = embed_model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k
    )
    
    if results and 'documents' in results and len(results['documents']) > 0:
        return results['documents'][0]
    return []
