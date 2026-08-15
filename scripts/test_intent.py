import asyncio
import os
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.services.llm.ollama import get_ollama_client
from api.core.prompts import INTENT_CLASSIFICATION_PROMPT

async def main():
    llm = get_ollama_client()
    user_message = "list all the proferssors"
    intent_prompt = INTENT_CLASSIFICATION_PROMPT.format(user_message=user_message)
    intent_result = await llm.generate_json(intent_prompt, fast_model=True)
    print("Intent Result:", intent_result)

if __name__ == "__main__":
    asyncio.run(main())
