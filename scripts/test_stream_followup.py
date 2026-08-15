import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.services.llm.ollama import get_ollama_client
from api.routes.chat import _handle_department_query_stream

async def main():
    llm = get_ollama_client()
    user_message = "what is his VoIP number?"
    conversation_context = "User: What is Bharat Sir's chamber number\nAssistant: According to the provided context documents, Bharat M. Deshpande ... has his office located at D-257 ... So, Bharat Sir's chamber number is D-257."
    
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
