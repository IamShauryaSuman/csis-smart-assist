from functools import lru_cache

from fastapi import HTTPException
from google import genai
from sentence_transformers import SentenceTransformer

from .config import Settings
from .schemas import ChatResponseOut
from .services import SupabaseService


@lru_cache
def get_embed_model() -> SentenceTransformer:
    return SentenceTransformer("intfloat/e5-base-v2")


class ChatService:
    def __init__(self, settings: Settings, supabase_service: SupabaseService) -> None:
        self.settings = settings
        self.supabase_service = supabase_service

    def answer_query(self, query: str, user_id: str) -> ChatResponseOut:
        try:
            embed_model = get_embed_model()
            embedding = embed_model.encode([query])[0].tolist()
            rag_rows = self.supabase_service.search_rag_chunks_from_embedding(
                embedding=embedding,
                match_count=5,
            )
            context = "\n".join(row.get("content", "") for row in rag_rows if row.get("content"))
            if not context:
                context = "No relevant knowledge chunks were found."

            prompt = f"""
You are CSIS SmartAssist. Answer the user query using the context below.
If the context is insufficient, say so briefly.

User ID: {user_id}

Context:
{context}

Question:
{query}
"""
            answer = self._generate_answer(prompt)
            sources = [
                {
                    "document_id": row.get("document_id"),
                    "chunk_index": row.get("chunk_index"),
                    "similarity": row.get("similarity"),
                }
                for row in rag_rows
            ]
            return ChatResponseOut(answer=answer, sources=sources)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Chat processing failed: {exc}") from exc

    def _generate_answer(self, prompt: str) -> str:
        if not self.settings.gemini_api_key:
            return "RAG retrieval succeeded, but GEMINI_API_KEY is not configured yet."

        client = genai.Client(api_key=self.settings.gemini_api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text or "I could not generate a response."
