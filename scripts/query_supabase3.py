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
    query_embedding = await llm.embed_query(search_query)
    
    match_result = db.rpc(
        "match_chunks",
        {
            "query_embedding": query_embedding,
            "match_threshold": 0.0,
            "match_count": 50,
        },
    ).execute()
    
    print("Finding Siddharth's email chunk:")
    for i, chunk in enumerate(match_result.data or []):
        if "siddharthg@goa.bits-pilani.ac.in" in chunk['content']:
            print(f"Rank {i+1}: Similarity {chunk['similarity']:.2f}")
            print(chunk['content'][:100])

if __name__ == "__main__":
    asyncio.run(main())
