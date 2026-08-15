import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.services.llm.ollama import get_ollama_client
from api.routes.chat import _handle_department_query

async def main():
    llm = get_ollama_client()
    
    # Let's monkey patch generate to just print the prompt
    original_generate = llm.generate
    async def fake_generate(prompt, system_prompt=None, **kwargs):
        print("--- SYSTEM PROMPT ---")
        print(system_prompt)
        print("--- USER PROMPT ---")
        print(prompt)
        return "FAKE RESPONSE"
    llm.generate = fake_generate
    
    user_message = "What is Siddharth Sir's Email Id"
    
    resp = await _handle_department_query(
        llm=llm,
        user_message=user_message,
        conversation_context="",
        memory_context="",
    )

if __name__ == "__main__":
    asyncio.run(main())
