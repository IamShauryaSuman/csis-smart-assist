import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.services.llm.ollama import get_ollama_client
from api.routes.chat import _handle_department_query_stream

async def main():
    llm = get_ollama_client()
    user_message = "what is Sanjay Kumar Sahay email id?"
    conversation_context = """User: What is Bharat Sir's VoIP?
Assistant: According to the provided context documents, Bharat M. Deshpande's VoIP (Office) number is 438.
Source: Source: Keyword Search Match (Relevance: 0.99) Sl. No. Name of Faculty Designation VoIP (O) PSRN New Chamber 6 Bharat M. Deshpande Professor 438 G0078 D-257 bmd@goa.bits-pilani.ac.in"""
    
    stream = _handle_department_query_stream(
        llm=llm,
        user_message=user_message,
        conversation_context=conversation_context,
        memory_context="",
    )
    
    print("AI Streamed Response: ", end="", flush=True)
    async for chunk in stream:
        print(chunk, end="", flush=True)
    print()

if __name__ == "__main__":
    asyncio.run(main())
