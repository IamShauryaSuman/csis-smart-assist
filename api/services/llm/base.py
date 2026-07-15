"""
Abstract base class for LLM integrations.

Encapsulates model interaction behind a generic interface so the backend
can swap between Gemini, a local Ollama instance, or any OpenAI-compatible
endpoint by implementing a single subclass — without modifying core logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """Interface contract for all LLM provider integrations."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        fast_model: bool = False,
    ) -> str:
        """Generate a text completion from the model.

        Args:
            prompt: The user-facing prompt / conversation turn.
            system_prompt: System-level instructions prepended to the context.
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative).
            max_tokens: Maximum tokens in the generated response.
            fast_model: Whether to use the faster, cheaper tier model.

        Returns:
            The model's text response.
        """
        ...

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        fast_model: bool = False,
    ):
        """Generate a text completion from the model as an async stream of chunks.

        Args:
            prompt: The user-facing prompt / conversation turn.
            system_prompt: System-level instructions prepended to the context.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the generated response.
            fast_model: Whether to use the faster, cheaper tier model.

        Yields:
            Chunks of the model's text response.
        """
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        ...

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.1,
        fast_model: bool = False,
    ) -> dict:
        """Generate a structured JSON response from the model.

        Args:
            prompt: The prompt expected to produce JSON.
            system_prompt: System-level instructions.
            temperature: Lower temperature for more deterministic JSON output.
            fast_model: Whether to use the faster, cheaper tier model.

        Returns:
            Parsed JSON as a Python dict.
        """
        ...
