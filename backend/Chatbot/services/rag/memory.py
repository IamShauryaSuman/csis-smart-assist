import os
import uuid
from google import genai
from Chatbot.core.config import settings
from Chatbot.services.rag.vector_store import client, embed_model

def get_gemini_client():
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set. Check your backend/.env")
    return genai.Client(api_key=api_key)

def summarize_conversation(text: str) -> str:
    """Summarizes a block of chat history using Gemini."""
    gemini_client = get_gemini_client()
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Summarize the following conversation concisely to be stored in memory:\n{text}"
    )
    return response.text

def add_to_memory(user_id: str, text: str):
    """Summarize text and store it in Chroma collection specific to the user."""
    collection_name = f"memory_{user_id.replace('-', '')}"
    try:
        collection = client.get_or_create_collection(name=collection_name)
    except Exception:
        # Fallback if names are invalid length
        collection = client.get_or_create_collection(name="global_memory")
        
    summarized = summarize_conversation(text)
    embedding = embed_model.encode([summarized]).tolist()
    
    collection.add(
        embeddings=embedding,
        documents=[summarized],
        ids=[f"mem_{uuid.uuid4().hex}"],
        metadatas=[{"user_id": user_id}]
    )

def retrieve_memory(user_id: str, query: str, top_k=3):
    """Retrieve relevant summarized past memories for a user given a query."""
    collection_name = f"memory_{user_id.replace('-', '')}"
    try:
        collection = client.get_or_create_collection(name=collection_name)
    except Exception:
        collection = client.get_or_create_collection(name="global_memory")
        
    if collection.count() == 0:
        return []
    
    query_embedding = embed_model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        where={"user_id": user_id} if collection.name == "global_memory" else None
    )
    
    if results and 'documents' in results and len(results['documents']) > 0:
        return results['documents'][0]
    return []
