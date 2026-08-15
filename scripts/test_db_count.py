import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")
from api.core.database import get_supabase_client

db = get_supabase_client()
keywords = ['Sanjay', 'Sahay', 'Kumar']
or_conds = ",".join(f"content.ilike.*{kw}*" for kw in keywords)

kw_resp = db.table("rag_chunks").select("id, content").or_(or_conds).execute()
print("Total matches:", len(kw_resp.data))

# Print which chunks contain Sanjay's email
for c in kw_resp.data:
    if "ssahay" in c["content"].lower():
        print("Found in chunk:", c["id"])

