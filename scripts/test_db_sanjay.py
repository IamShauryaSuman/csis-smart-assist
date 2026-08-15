import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")
from api.core.database import get_supabase_client

db = get_supabase_client()
keywords = ['Sanjay', 'Sahay', 'Kumar']

or_conds = ",".join(f"content.ilike.*{kw}*" for kw in keywords)
print("OR CONDITIONS:", or_conds)

kw_resp = db.table("rag_chunks").select("id, content").or_(or_conds).limit(5).execute()

for c in kw_resp.data:
    print("---")
    print("CHUNK ID:", c["id"])
    
    matched_lines = [line.strip() for line in c["content"].split("\n") 
                     if any(kw.lower() in line.lower() for kw in keywords)]
    print("MATCHED LINES:", matched_lines)

