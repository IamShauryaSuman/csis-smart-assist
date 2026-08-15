import os
import httpx
from dotenv import load_dotenv

load_dotenv()
supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

headers = {
    "apikey": supabase_key,
    "Authorization": f"Bearer {supabase_key}",
    "Content-Type": "application/json"
}

resp = httpx.get(f"{supabase_url}/rest/v1/rag_chunks?select=content&content=ilike.*Ashwin*", headers=headers)
print("Ashwin chunks:", resp.json())

resp2 = httpx.get(f"{supabase_url}/rest/v1/rag_chunks?select=content&content=ilike.*D-209*", headers=headers)
print("D-209 chunks:", resp2.json())
