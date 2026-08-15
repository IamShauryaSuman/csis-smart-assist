import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.services.llm.ollama import get_ollama_client
from api.routes.chat import _handle_department_query_stream

class MockBody:
    message = "What is Siddharth Sir's Email Id"
    session_id = "test"

async def main():
    llm = get_ollama_client()
    
    # We just want to print the generated response.
    # We have to mock the async generator output.
    
    # Wait, the simplest way is to just call the API directly using httpx
    pass

