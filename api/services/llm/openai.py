"""
Generic OpenAI-compatible LLM integration.

Can be used for OpenRouter, Groq, or any other provider that matches the OpenAI API spec.
"""

import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI
from services.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class OpenAICompatibleClient(BaseLLMClient):
    """Implementation of the LLM interface using the official OpenAI async client."""

    def __init__(self, api_key: str, base_url: str, default_model: str):
        self._model = default_model
        if not api_key:
            logger.warning(f"No API key provided for OpenAI-compatible endpoint at {base_url}. Calls will likely fail.")
        
        self._client = AsyncOpenAI(api_key=api_key or "dummy", base_url=base_url)

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        fast_model: bool = False,
    ) -> str:
        """Generate a text completion."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    async def generate_stream(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        fast_model: bool = False,
    ):
        """Generate a text completion as an async stream."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                content = chunk.choices[0].delta.content
                if content:
                    yield content

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector. Not typically supported by Groq/OpenRouter efficiently for our use case."""
        raise NotImplementedError("Embeddings must be routed to Gemini to maintain vector DB compatibility.")

    async def embed_query(self, text: str) -> list[float]:
        """Generate a query embedding vector."""
        raise NotImplementedError("Embeddings must be routed to Gemini to maintain vector DB compatibility.")

    async def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.1,
        fast_model: bool = False,
    ) -> dict[str, Any]:
        """Generate structured JSON."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=2048,
            response_format={"type": "json_object"} if "groq" in str(self._client.base_url).lower() else None,
        )
        
        raw_text = response.choices[0].message.content or ""
        raw_text = raw_text.strip()

        # Handle markdown fences if the model still outputs them
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw_text)
        if json_match:
            raw_text = json_match.group(1).strip()

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON response from OpenAI-compatible provider: %s", raw_text[:200])
            return {"error": "Failed to parse response", "raw": raw_text}
