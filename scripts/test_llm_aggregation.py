import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.services.llm.ollama import get_ollama_client
from api.routes.chat import _handle_department_query_stream

async def main():
    llm = get_ollama_client()
    user_message = "how many profs are there in the cs department"
    
    stream = _handle_department_query_stream(
        llm=llm,
        user_message=user_message,
        conversation_context="",
        memory_context="",
    )
    
    print("AI Streamed Response: ", end="", flush=True)
    async for chunk in stream:
        print(chunk, end="", flush=True)
    print()

if __name__ == "__main__":
    asyncio.run(main())
