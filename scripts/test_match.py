import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.services.llm.ollama import get_ollama_client
from api.core.database import get_supabase_client

async def main():
    llm = get_ollama_client()
    db = get_supabase_client()
    search_query = "User: What is Bharat Sir's chamber number Assistant: According to the provided context documents, Bharat M. Deshpande ... has his office located at D-257 ... So, Bharat Sir's chamber number is D-257. what is his VoIP number?"
    
    query_embedding = await llm.embed_query(search_query)
    match_result = db.rpc(
        "match_chunks",
        {
            "query_embedding": query_embedding,
            "match_threshold": 0.2,
            "match_count": 15,
        },
    ).execute()
    
    if match_result.data:
        for chunk in match_result.data[:5]:
            print("SIMILARITY:", chunk["similarity"])
            print("CONTENT:\n", chunk["content"][:200])
            print("---")
    else:
        print("NO MATCHES")

if __name__ == "__main__":
    asyncio.run(main())
