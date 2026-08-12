"""
Local LLM Client — single-provider wrapper around OllamaClient.

Replaces the multi-cloud HybridLLMClient with a clean, direct-delegation
layer.  No fallback chains, no API key rotation — just one local Ollama
server powering everything.

Easy to extend: swap OllamaClient for any other BaseLLMClient subclass
(vLLM, llama.cpp HTTP, text-generation-inference) with zero route changes.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from services.llm.base import BaseLLMClient
from services.llm.ollama import OllamaClient

logger = logging.getLogger(__name__)


class LocalLLMClient(BaseLLMClient):
    """Thin wrapper that delegates every call to a single local provider.

    The interface is intentionally identical to HybridLLMClient so that
    routes need only an import-path change.
    """

    def __init__(self) -> None:
        self.provider = OllamaClient()

    # ── Text Generation ────────────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        fast_model: bool = False,
    ) -> str:
        """Generate a text completion using the local model."""
        return await self.provider.generate(
            prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            fast_model=fast_model,
        )

    async def generate_stream(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        fast_model: bool = False,
    ):
        """Stream a text completion from the local model."""
        async for chunk in self.provider.generate_stream(
            prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            fast_model=fast_model,
        ):
            yield chunk

    # ── JSON Generation ────────────────────────────────────────────────────

    async def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.1,
        fast_model: bool = False,
    ) -> dict:
        """Generate structured JSON.  Uses fast model by default for intent classification."""
        return await self.provider.generate_json(
            prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            fast_model=fast_model,
        )

    # ── Embeddings ─────────────────────────────────────────────────────────

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for document storage."""
        return await self.provider.embed(text)

    async def embed_query(self, text: str) -> list[float]:
        """Generate an embedding vector for similarity search queries."""
        return await self.provider.embed_query(text)

    # ── Convenience Methods (match HybridLLMClient API) ────────────────────

    async def generate_title(self, prompt: str) -> str:
        """Generate a short chat session title.  Uses fast model + low temp."""
        return await self.provider.generate(
            prompt, temperature=0.3, max_tokens=50, fast_model=True,
        )

    async def generate_memory(self, prompt: str) -> str:
        """Synthesize long-term memory from a conversation.  Uses fast model."""
        return await self.provider.generate(
            prompt, temperature=0.2, max_tokens=1024, fast_model=True,
        )


@lru_cache(maxsize=1)
def get_local_client() -> LocalLLMClient:
    """Singleton accessor for the local LLM client."""
    return LocalLLMClient()
