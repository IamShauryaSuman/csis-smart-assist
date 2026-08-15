import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.services.llm.ollama import get_ollama_client
from api.core.database import get_supabase_client
import re
from api.routes.chat import _prepare_search_query

async def main():
    llm = get_ollama_client()
    db = get_supabase_client()
    user_message = "What is Siddharth Sir's Email Id"
    
    keywords = [w for w in set(re.findall(r'\b[a-zA-Z]{4,}\b', user_message)) 
                if w.lower() not in {"what", "when", "where", "which", "who", "whom", "whose", "why", "how", "this", "that", "these", "those", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "shall", "should", "can", "could", "may", "might", "must", "about", "above", "across", "after", "against", "along", "among", "around", "at", "before", "behind", "below", "beneath", "beside", "between", "beyond", "but", "by", "concerning", "considering", "despite", "down", "during", "except", "for", "from", "in", "inside", "into", "like", "near", "of", "off", "on", "onto", "out", "outside", "over", "past", "regarding", "round", "since", "through", "throughout", "till", "to", "toward", "under", "underneath", "until", "up", "upon", "with", "within", "without", "number", "email", "office", "chamber", "room", "department", "csis", "bits", "pilani"}]
    
    hybrid_chunks = []
    if keywords:
        or_conds = ",".join(f"content.ilike.*{kw}*" for kw in keywords)
        kw_resp = db.table("rag_chunks").select("id, content").or_(or_conds).limit(5).execute()
        if kw_resp.data:
            for kw_chunk in kw_resp.data:
                kw_chunk["similarity"] = 0.99  # Keyword match score
                kw_chunk["file_name"] = "Keyword Search Match"
                hybrid_chunks.append(kw_chunk)
                
    print("HYBRID CHUNKS LEN:", len(hybrid_chunks))
    if hybrid_chunks:
        print(hybrid_chunks[0])

if __name__ == "__main__":
    asyncio.run(main())
