import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.services.llm.ollama import get_ollama_client
from api.core.prompts import DEPARTMENT_RAG_SYSTEM_PROMPT

async def main():
    llm = get_ollama_client()
    
    rag_context = """
**Source: Keyword Search Match** (Relevance: 0.99)
Gawali Assistant Professor, Gr-I 269 G0700 D-263 shubhangi@goa.bits-pilani.ac.in
21 Siddharth Gupta Assistant Professor, Gr-I 857 G0962 D-260 siddharthg@goa.bits-pilani.ac.in
22 Snehanshu  Saha Associ
"""
    
    system_prompt = DEPARTMENT_RAG_SYSTEM_PROMPT.format(
        memory_context="",
        rag_context=rag_context,
    )
    
    full_prompt = f"Conversation history:\n\nCurrent question: What is Siddharth Sir's Email Id"
    resp = await llm.generate(full_prompt, system_prompt=system_prompt)
    print("AI Response:")
    print(resp)

if __name__ == "__main__":
    asyncio.run(main())
