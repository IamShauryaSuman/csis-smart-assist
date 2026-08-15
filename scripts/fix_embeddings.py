import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.services.llm.ollama import get_ollama_client
from api.core.database import get_supabase_client

async def main():
    llm = get_ollama_client()
    db = get_supabase_client()
    
    # Fetch all chunks
    resp = db.table("rag_chunks").select("id, content").execute()
    chunks = resp.data or []
    print(f"Found {len(chunks)} chunks to re-embed.")
    
    for idx, chunk in enumerate(chunks):
        content = chunk["content"]
        chunk_id = chunk["id"]
        
        # Re-embed using nomic-embed-text
        embedding = await llm.embed(content)
        
        # Update database
        db.table("rag_chunks").update({"embedding": embedding}).eq("id", chunk_id).execute()
        
        if (idx + 1) % 10 == 0:
            print(f"Processed {idx + 1}/{len(chunks)} chunks...")
            
    print("Done! Re-embedded all chunks with nomic-embed-text.")

if __name__ == "__main__":
    asyncio.run(main())
