import asyncio
from dotenv import load_dotenv

load_dotenv("api/.env")
from api.core.database import get_supabase_client

db = get_supabase_client()
res = db.table("rag_chunks").select("id, file_id, file_name").limit(1).execute()
print(res.data)
