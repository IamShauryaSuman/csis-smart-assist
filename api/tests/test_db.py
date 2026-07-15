import asyncio
from core.database import get_supabase_client
db = get_supabase_client()
res = db.table("messages").select("id, created_at, role, content").order("created_at", desc=True).limit(10).execute()
for m in res.data:
    print(f"{m['created_at']} | {m['role']} | {m['content'][:50]}")
