import asyncio
from services.llm.gemini import get_gemini_client

async def main():
    llm = get_gemini_client()
    print("Sending request to Gemini...")
    try:
        res = await llm.generate("Hello, just testing.")
        print(f"Response: {res}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
