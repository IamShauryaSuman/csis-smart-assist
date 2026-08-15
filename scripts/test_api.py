import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.services.llm.ollama import get_ollama_client
from api.routes.chat import _handle_department_query, _handle_general_query, _prepare_search_query
from api.core.prompts import INTENT_CLASSIFICATION_PROMPT

async def main():
    llm = get_ollama_client()
    
    msg = "What is Ashwin Sir's Chamber number?"
    
    # 1. Test Intent Classification
    intent_prompt = INTENT_CLASSIFICATION_PROMPT.format(user_message=msg)
    intent = await llm.generate_json(intent_prompt, fast_model=True)
    print("Intent:", intent)
    
    # 2. Test RAG Search Query
    search_query = _prepare_search_query(msg, "")
    print("Search Query:", search_query)
    
    # 3. Test RAG response
    resp = await _handle_department_query(llm, msg, "", "")
    print("RAG Response:", resp)

if __name__ == "__main__":
    asyncio.run(main())
