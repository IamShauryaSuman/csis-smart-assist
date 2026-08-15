import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.services.llm.ollama import get_ollama_client
from api.routes.chat import _handle_department_query_stream

async def main():
    llm = get_ollama_client()
    user_message = "what is Sanjay Kumar Sahay email id?"
    
    memory_context = "USER CONTEXT (Personalization Data):\n- Name: Arnav Gupta\n- Role: Student\n- Department: Computer Science\n- Year: 2nd Year"
    
    stream = _handle_department_query_stream(
        llm=llm,
        user_message=user_message,
        conversation_context="",
        memory_context=memory_context,
    )
    
    print("AI Streamed Response: ", end="", flush=True)
    async for chunk in stream:
        print(chunk, end="", flush=True)
    print()

if __name__ == "__main__":
    asyncio.run(main())
