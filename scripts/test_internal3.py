import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.core.database import get_supabase_client

db = get_supabase_client()
keywords = ["Siddharth"]
or_conds = ",".join(f"content.ilike.*{kw}*" for kw in keywords)
kw_resp = db.table("rag_chunks").select("id, content").or_(or_conds).limit(5).execute()
print("kw_resp.data:", len(kw_resp.data or []))
