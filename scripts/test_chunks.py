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
    
    user_message = "list all the proferssors"
    search_query = _prepare_search_query(user_message, "")
    query_embedding = await llm.embed_query(search_query)
    
    match_result = db.rpc(
        "match_chunks",
        {
            "query_embedding": query_embedding,
            "match_threshold": 0.2,
            "match_count": 30,
        },
    ).execute()
    
    for c in match_result.data:
        print(f"File: {c.get('file_name', 'Unknown')}, Sim: {c.get('similarity', 0)}")
        print(c.get('content', '')[:100])
        print("---")

if __name__ == "__main__":
    asyncio.run(main())
