"""
Google Gemini LLM integration.

Concrete implementation of BaseLLMClient using the google-generativeai SDK.
Handles text generation, embedding, and structured JSON extraction.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from typing import Any

import google.generativeai as genai

from core.config import get_settings
from services.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class GeminiClient(BaseLLMClient):
    """Gemini 2.5 Flash implementation of the LLM interface."""

    def __init__(self) -> None:
        settings = get_settings()
        
        # Force genai to ignore ADC which causes ACCESS_TOKEN_TYPE_UNSUPPORTED errors
        import os
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        
        genai.configure(api_key=settings.gemini_api_key)
        
        self._model_name = settings.gemini_model
        self._fast_model_name = settings.gemini_fast_model
        self._embedding_model_name = settings.gemini_embedding_model

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
        fast_model: bool = False,
    ) -> str:
        """Generate a text completion using Gemini."""
        model = genai.GenerativeModel(
            model_name=self._fast_model_name if fast_model else self._model_name,
            system_instruction=system_prompt if system_prompt else None,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        response = await model.generate_content_async(prompt)

        if not response.candidates:
            logger.warning("Gemini returned no candidates for prompt: %s", prompt[:100])
            return "I'm sorry, I couldn't generate a response. Please try rephrasing your question."

        return response.text

    async def generate_stream(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
        fast_model: bool = False,
    ):
        """Generate a text completion using Gemini as an async stream."""
        model = genai.GenerativeModel(
            model_name=self._fast_model_name if fast_model else self._model_name,
            system_instruction=system_prompt if system_prompt else None,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        response = await model.generate_content_async(prompt, stream=True)
        async for chunk in response:
            if chunk.text:
                yield chunk.text

    async def embed(self, text: str) -> list[float]:
        """Generate a 768-dim embedding using gemini-embedding-001."""
        result = await genai.embed_content_async(
            model=self._embedding_model_name,
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"][:768]

    async def embed_query(self, text: str) -> list[float]:
        """Generate a query embedding (uses retrieval_query task type)."""
        result = await genai.embed_content_async(
            model=self._embedding_model_name,
            content=text,
            task_type="retrieval_query",
        )
        return result["embedding"][:768]

    async def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.1,
        fast_model: bool = False,
    ) -> dict[str, Any]:
        """Generate structured JSON from Gemini and parse it."""
        model = genai.GenerativeModel(
            model_name=self._fast_model_name if fast_model else self._model_name,
            system_instruction=system_prompt if system_prompt else None,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )
        response = await model.generate_content_async(prompt)

        if not response.candidates:
            logger.warning("Gemini JSON generation returned no candidates")
            return {"error": "No response generated"}

        raw_text = response.text.strip()

        # Attempt to extract JSON from the response, handling markdown fences
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw_text)
        if json_match:
            raw_text = json_match.group(1).strip()

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse Gemini JSON response: %s", raw_text[:200])
            return {"error": "Failed to parse response", "raw": raw_text}


@lru_cache(maxsize=1)
def get_gemini_client() -> GeminiClient:
    """Singleton accessor for the Gemini client."""
    return GeminiClient()
