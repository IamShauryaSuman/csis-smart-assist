import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.services.llm.ollama import get_ollama_client
from api.core.database import get_supabase_client
from api.routes.chat import _prepare_search_query

async def main():
    llm = get_ollama_client()
    db = get_supabase_client()
    
    msg = "What is Siddharth Sir's Email Id"
    search_query = _prepare_search_query(msg, "")
    print("Search query:", search_query)
    
    query_embedding = await llm.embed_query(search_query)
    
    match_result = db.rpc(
        "match_chunks",
        {
            "query_embedding": query_embedding,
            "match_threshold": 0.2,
            "match_count": 10,
        },
    ).execute()
    
    print("Matched chunks (Threshold 0.2):")
    for chunk in (match_result.data or []):
        print(f"Similarity: {chunk['similarity']:.2f}")
        print(chunk['content'][:200])
        print("---")
        
    print("Checking if Siddharth exists in DB at all...")
    resp = db.table("rag_chunks").select("content").ilike("content", "%Siddharth%").execute()
    print("Siddharth chunks in DB:", len(resp.data or []))
    for chunk in (resp.data or []):
        print(chunk['content'][:200])
        print("---")

if __name__ == "__main__":
    asyncio.run(main())
