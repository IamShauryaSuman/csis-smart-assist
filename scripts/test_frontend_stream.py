import asyncio
from httpx import AsyncClient

async def test():
    async with AsyncClient() as client:
        pass
