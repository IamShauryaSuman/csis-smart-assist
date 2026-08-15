import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.core.database import get_supabase_client

db = get_supabase_client()
print("Testing * wildcard:")
resp1 = db.table("rag_chunks").select("id, content").or_("content.ilike.*Siddharth*").execute()
print(len(resp1.data or []))

print("Testing % wildcard:")
resp2 = db.table("rag_chunks").select("id, content").or_("content.ilike.%Siddharth%").execute()
print(len(resp2.data or []))
