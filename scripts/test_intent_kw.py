import asyncio
from dotenv import load_dotenv

load_dotenv("api/.env")

from api.services.llm.ollama import get_ollama_client

async def main():
    llm = get_ollama_client()
    user_message = "list all the proferssors"
    
    prompt = """You are an intent classifier for CSIS SmartAssist, the AI assistant for the Computer Science & Information Systems (CSIS) Department at BITS Pilani, K K Birla Goa Campus.

Classify the user's message into EXACTLY ONE of these three intents:
1. "department_query"
2. "calendar_query"
3. "general_query"

You must also generate a list of 1 to 5 optimized search keywords for querying a vector database. Fix any typos in the user's message and use domain-specific synonyms if helpful (e.g., if they say 'prof', use 'professor', 'faculty').

Respond with ONLY a JSON object in this exact format, no other text:
{"intent": "<one of: department_query, calendar_query, general_query>", "confidence": <float>, "keywords": ["keyword1", "keyword2"]}

User message: """ + user_message
    
    intent_result = await llm.generate_json(prompt, fast_model=True)
    print("Result:", intent_result)

if __name__ == "__main__":
    asyncio.run(main())
