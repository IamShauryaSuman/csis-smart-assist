"""
Ollama LLM integration for fully local inference.

Concrete implementation of BaseLLMClient that communicates with an Ollama
server over its REST API using httpx.  No external SDK required — just HTTP.

Supports text generation, streaming, JSON-mode output, and embeddings via
locally-hosted models (e.g. Llama 3, Mistral Nemo, bge-m3).
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from typing import Any

import httpx

from core.config import get_settings
from services.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)

# Generous timeout: large local models can be slow on first load.
_DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)


class OllamaClient(BaseLLMClient):
    """LLM client backed by a local Ollama instance."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._fast_model = settings.ollama_fast_model
        self._embedding_model = settings.ollama_embedding_model
        self._embedding_dim = settings.embedding_dimension

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _pick_model(self, fast: bool) -> str:
        return self._fast_model if fast else self._model

    def _chat_url(self) -> str:
        return f"{self._base_url}/api/chat"

    def _embed_url(self) -> str:
        return f"{self._base_url}/api/embed"

    @staticmethod
    def _build_messages(prompt: str, system_prompt: str) -> list[dict[str, str]]:
        msgs: list[dict[str, str]] = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": prompt})
        return msgs

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
        """Generate a text completion via Ollama (non-streaming)."""
        payload = {
            "model": self._pick_model(fast_model),
            "messages": self._build_messages(prompt, system_prompt),
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.post(self._chat_url(), json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("message", {}).get("content", "")
        if not content:
            logger.warning("Ollama returned empty content for prompt: %s", prompt[:100])
            return "I'm sorry, I couldn't generate a response. Please try rephrasing your question."
        return content

    # ── Streaming Generation ───────────────────────────────────────────────

    async def generate_stream(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        fast_model: bool = False,
    ):
        """Generate a text completion as an async stream of chunks."""
        payload = {
            "model": self._pick_model(fast_model),
            "messages": self._build_messages(prompt, system_prompt),
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            async with client.stream("POST", self._chat_url(), json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    text = chunk.get("message", {}).get("content", "")
                    if text:
                        yield text

    # ── Embeddings ─────────────────────────────────────────────────────────

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector using the local embedding model.

        Truncates to ``self._embedding_dim`` dimensions to match the
        existing pgvector column definition.
        """
        payload = {
            "model": self._embedding_model,
            "input": text,
        }

        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.post(self._embed_url(), json=payload)
            resp.raise_for_status()
            data = resp.json()

        # Ollama returns {"embeddings": [[...], ...]}
        embeddings = data.get("embeddings", [])
        if not embeddings:
            raise ValueError("Ollama returned no embeddings.")
        vector = embeddings[0]
        return vector[: self._embedding_dim]

    async def embed_query(self, text: str) -> list[float]:
        """Generate a query embedding (same as embed for bge-m3)."""
        return await self.embed(text)

    # ── JSON Generation ────────────────────────────────────────────────────

    async def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.1,
        fast_model: bool = False,
    ) -> dict[str, Any]:
        """Generate a structured JSON response using Ollama's native JSON mode."""
        payload = {
            "model": self._pick_model(fast_model),
            "messages": self._build_messages(prompt, system_prompt),
            "stream": False,
            "format": "json",
            "options": {
                "temperature": temperature,
            },
        }

        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.post(self._chat_url(), json=payload)
            resp.raise_for_status()
            data = resp.json()

        raw_text = data.get("message", {}).get("content", "").strip()

        # Handle markdown fences if the model still wraps output
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw_text)
        if json_match:
            raw_text = json_match.group(1).strip()

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse Ollama JSON response: %s", raw_text[:200])
            return {"error": "Failed to parse response", "raw": raw_text}


@lru_cache(maxsize=1)
def get_ollama_client() -> OllamaClient:
    """Singleton accessor for the Ollama client."""
    return OllamaClient()
