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
Sl. No. Name of Faculty Designation VoIP (O) PSRN New Chamber No. Email ID Date of Joining

---

**Source: Keyword Search Match** (Relevance: 0.99)
6 Bharat M. Deshpande Professor 438 G0078 D-257 bmd@goa.bits-pilani.ac.in
"""
    
    system_prompt = DEPARTMENT_RAG_SYSTEM_PROMPT.format(
        memory_context="",
        rag_context=rag_context,
    )
    
    full_prompt = f"Conversation history:\nUser: What is Bharat Sir's chamber number\nAssistant: According to the provided context documents, Bharat M. Deshpande ... has his office located at D-257 ... So, Bharat Sir's chamber number is D-257.\n\nCurrent question: what is his VoIP number?"
    
    stream = llm.generate_stream(full_prompt, system_prompt=system_prompt)
    print("AI Streamed Response: ", end="", flush=True)
    async for chunk in stream:
        print(chunk, end="", flush=True)
    print()

if __name__ == "__main__":
    asyncio.run(main())
