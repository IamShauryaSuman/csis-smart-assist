import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.core.database import get_supabase_client

db = get_supabase_client()
resp = db.table("rag_chunks").select("embedding").limit(1).execute()
if resp.data and resp.data[0]['embedding']:
    emb = resp.data[0]['embedding']
    if isinstance(emb, str):
        emb = eval(emb)
    print("Embedding length:", len(emb))
else:
    print("No data")
