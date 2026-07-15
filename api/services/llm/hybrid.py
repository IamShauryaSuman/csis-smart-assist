"""
Hybrid LLM Client combining Gemini, Groq, and OpenRouter with strict fallback logic.

- Response Generation: Primary: Gemini -> Fallback: Groq -> Fallback: OpenRouter
- Intent Classification: Primary: Groq -> Fallback: Gemini -> Fallback: OpenRouter
- Title Generation: Primary: OpenRouter -> Fallback: Groq -> Fallback: Gemini
- Embeddings: Primary: Gemini (no fallback to maintain vector DB compatibility)
"""

import logging
from typing import Any
from functools import lru_cache

from core.config import get_settings
from services.llm.base import BaseLLMClient
from services.llm.gemini import GeminiClient
from services.llm.openai import OpenAICompatibleClient

logger = logging.getLogger(__name__)


class HybridLLMClient(BaseLLMClient):
    """Hybrid client that manages fallback between Gemini, Groq, and OpenRouter."""

    def __init__(self):
        settings = get_settings()

        # Initialize providers
        self.gemini = GeminiClient()
        self.groq = OpenAICompatibleClient(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            default_model=settings.groq_model,
        )
        self.openrouter = OpenAICompatibleClient(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            default_model=settings.openrouter_model,
        )

    async def _execute_with_fallback(self, method_name: str, chain: list[BaseLLMClient], *args, **kwargs):
        """Execute a method across a chain of clients, falling back on error."""
        last_exception = None
        for i, client in enumerate(chain):
            provider_name = client.__class__.__name__
            if provider_name == "OpenAICompatibleClient":
                provider_name = "Groq" if "groq" in str(client._client.base_url) else "OpenRouter"

            try:
                method = getattr(client, method_name)
                
                if method_name == "generate_stream":
                    # For streaming, we must capture the stream and yield it
                    # We can't await an async generator. We just iterate it.
                    # However, to catch connection errors, we yield from it inside the try block.
                    # But yielding inside a try/except that contains a loop is complex.
                    # Instead, we return the async generator.
                    pass # Handled separately below
                
                return await method(*args, **kwargs)
            
            except Exception as e:
                err_msg = str(e).lower()
                # If it's the last client in the chain, raise the error
                if i == len(chain) - 1:
                    logger.error(f"All fallback providers exhausted for {method_name}. Last error from {provider_name}: {e}")
                    raise
                
                # Check if error is retryable/fallbackable
                if any(x in err_msg for x in ["429", "quota", "exhausted", "500", "502", "503", "timeout"]):
                    logger.warning(f"Provider {provider_name} failed with {e}. Falling back to next provider...")
                    continue
                else:
                    logger.warning(f"Provider {provider_name} failed with unexpected error {e}. Falling back...")
                    continue

    async def _execute_stream_with_fallback(self, method_name: str, chain: list[BaseLLMClient], *args, **kwargs):
        """Execute a streaming method across a chain, falling back on initial connection error."""
        for i, client in enumerate(chain):
            provider_name = client.__class__.__name__
            if provider_name == "OpenAICompatibleClient":
                provider_name = "Groq" if "groq" in str(client._client.base_url) else "OpenRouter"

            try:
                method = getattr(client, method_name)
                # We start iterating the stream. If it connects successfully and yields the first chunk, 
                # we consider it successful and yield all remaining chunks.
                # If it fails before the first chunk (e.g. 429 rate limit), it will be caught here.
                async for chunk in method(*args, **kwargs):
                    yield chunk
                return # Successfully streamed entirely, exit the fallback loop
            except Exception as e:
                err_msg = str(e).lower()
                if i == len(chain) - 1:
                    logger.error(f"All fallback providers exhausted for stream. Last error: {e}")
                    raise
                if any(x in err_msg for x in ["429", "quota", "exhausted", "500", "502", "503", "timeout"]):
                    logger.warning(f"Provider {provider_name} stream failed with {e}. Falling back...")
                    continue
                else:
                    logger.warning(f"Provider {provider_name} stream failed with unexpected {e}. Falling back...")
                    continue

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        fast_model: bool = False,
    ) -> str:
        """Response Generation: Gemini -> Groq -> OpenRouter"""
        chain = [self.gemini, self.groq, self.openrouter]
        return await self._execute_with_fallback(
            "generate", chain, prompt, system_prompt=system_prompt, temperature=temperature, max_tokens=max_tokens, fast_model=fast_model
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
        """Response Generation: Gemini -> Groq -> OpenRouter"""
        chain = [self.gemini, self.groq, self.openrouter]
        async for chunk in self._execute_stream_with_fallback(
            "generate_stream", chain, prompt, system_prompt=system_prompt, temperature=temperature, max_tokens=max_tokens, fast_model=fast_model
        ):
            yield chunk

    async def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.1,
        fast_model: bool = False,
    ) -> dict:
        """Intent Classification: Groq -> Gemini -> OpenRouter"""
        chain = [self.groq, self.gemini, self.openrouter]
        return await self._execute_with_fallback(
            "generate_json", chain, prompt, system_prompt=system_prompt, temperature=temperature, fast_model=fast_model
        )

    async def embed(self, text: str) -> list[float]:
        """Embeddings: strictly Gemini."""
        return await self.gemini.embed(text)

    async def embed_query(self, text: str) -> list[float]:
        """Query Embeddings: strictly Gemini."""
        return await self.gemini.embed_query(text)
    
    async def generate_title(self, prompt: str) -> str:
        """Title Generation: OpenRouter -> Groq -> Gemini"""
        chain = [self.openrouter, self.groq, self.gemini]
        return await self._execute_with_fallback(
            "generate", chain, prompt, temperature=0.3, max_tokens=50
        )

    async def generate_memory(self, prompt: str) -> str:
        """Memory Synthesis: Groq -> OpenRouter -> Gemini"""
        chain = [self.groq, self.openrouter, self.gemini]
        return await self._execute_with_fallback(
            "generate", chain, prompt, temperature=0.2, max_tokens=1024
        )


@lru_cache(maxsize=1)
def get_hybrid_client() -> HybridLLMClient:
    """Singleton accessor for the hybrid LLM client."""
    return HybridLLMClient()
