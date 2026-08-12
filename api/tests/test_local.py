"""
Tests for the local LLM infrastructure (OllamaClient + LocalLLMClient).

All Ollama HTTP calls are mocked via httpx — no running Ollama instance required.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from services.llm.ollama import OllamaClient
from services.llm.local import LocalLLMClient


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_settings():
    """Provide mock settings for OllamaClient initialization."""
    settings = MagicMock()
    settings.ollama_base_url = "http://localhost:11434"
    settings.ollama_model = "llama3:70b"
    settings.ollama_fast_model = "llama3:8b"
    settings.ollama_embedding_model = "bge-m3"
    settings.embedding_dimension = 768
    return settings


@pytest.fixture
def ollama_client(mock_settings):
    """Create an OllamaClient with mocked settings."""
    with patch("services.llm.ollama.get_settings", return_value=mock_settings):
        return OllamaClient()


@pytest.fixture
def local_client(mock_settings):
    """Create a LocalLLMClient backed by a mocked OllamaClient."""
    with patch("services.llm.ollama.get_settings", return_value=mock_settings):
        return LocalLLMClient()


# ── OllamaClient Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_success(ollama_client):
    """Test non-streaming text generation."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"role": "assistant", "content": "Hello from Ollama!"},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await ollama_client.generate("Hello")

    assert result == "Hello from Ollama!"
    instance.post.assert_called_once()
    call_args = instance.post.call_args
    assert call_args[0][0] == "http://localhost:11434/api/chat"
    payload = call_args[1]["json"]
    assert payload["model"] == "llama3:70b"
    assert payload["stream"] is False


@pytest.mark.asyncio
async def test_generate_with_fast_model(ollama_client):
    """Test that fast_model=True uses the smaller model."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"role": "assistant", "content": "Fast response"},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        await ollama_client.generate("Hello", fast_model=True)

    payload = instance.post.call_args[1]["json"]
    assert payload["model"] == "llama3:8b"


@pytest.mark.asyncio
async def test_generate_empty_content(ollama_client):
    """Test fallback message when Ollama returns empty content."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"message": {"content": ""}}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await ollama_client.generate("Hello")

    assert "sorry" in result.lower()


@pytest.mark.asyncio
async def test_generate_json_success(ollama_client):
    """Test JSON-mode generation and parsing."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {
            "content": '{"intent": "department_query", "confidence": 0.95}',
        },
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await ollama_client.generate_json("Classify this")

    assert result["intent"] == "department_query"
    assert result["confidence"] == 0.95
    # Verify JSON mode was requested
    payload = instance.post.call_args[1]["json"]
    assert payload["format"] == "json"


@pytest.mark.asyncio
async def test_generate_json_with_markdown_fences(ollama_client):
    """Test that markdown-fenced JSON is still parsed correctly."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {
            "content": '```json\n{"intent": "calendar_query"}\n```',
        },
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await ollama_client.generate_json("Classify this")

    assert result["intent"] == "calendar_query"


@pytest.mark.asyncio
async def test_generate_json_parse_failure(ollama_client):
    """Test graceful handling of unparseable JSON responses."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"content": "not valid json at all"},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await ollama_client.generate_json("Classify this")

    assert "error" in result


@pytest.mark.asyncio
async def test_embed_success(ollama_client):
    """Test embedding generation with dimension truncation."""
    full_vector = [0.1] * 1024  # bge-m3 outputs 1024 dims
    mock_response = MagicMock()
    mock_response.json.return_value = {"embeddings": [full_vector]}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await ollama_client.embed("Some text to embed")

    assert len(result) == 768  # Truncated to match pgvector schema
    assert all(v == 0.1 for v in result)
    # Verify correct endpoint
    call_args = instance.post.call_args
    assert call_args[0][0] == "http://localhost:11434/api/embed"


@pytest.mark.asyncio
async def test_embed_empty_response(ollama_client):
    """Test error handling when Ollama returns no embeddings."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"embeddings": []}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        with pytest.raises(ValueError, match="no embeddings"):
            await ollama_client.embed("Some text")


@pytest.mark.asyncio
async def test_embed_query_delegates_to_embed(ollama_client):
    """Test that embed_query() calls embed() (same for bge-m3)."""
    vector = [0.5] * 768
    mock_response = MagicMock()
    mock_response.json.return_value = {"embeddings": [vector]}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await ollama_client.embed_query("Query text")

    assert len(result) == 768


# ── LocalLLMClient Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_local_client_delegates_generate(local_client):
    """Test that LocalLLMClient.generate delegates to OllamaClient."""
    local_client.provider = AsyncMock()
    local_client.provider.generate.return_value = "Local response"

    result = await local_client.generate("Hello", system_prompt="Be helpful")

    assert result == "Local response"
    local_client.provider.generate.assert_called_once_with(
        "Hello",
        system_prompt="Be helpful",
        temperature=0.7,
        max_tokens=4096,
        fast_model=False,
    )


@pytest.mark.asyncio
async def test_local_client_delegates_generate_json(local_client):
    """Test that generate_json delegates correctly."""
    local_client.provider = AsyncMock()
    local_client.provider.generate_json.return_value = {"intent": "general_query"}

    result = await local_client.generate_json("Test")

    assert result["intent"] == "general_query"
    local_client.provider.generate_json.assert_called_once()


@pytest.mark.asyncio
async def test_local_client_delegates_embed(local_client):
    """Test that embed delegates correctly."""
    local_client.provider = AsyncMock()
    local_client.provider.embed.return_value = [0.1] * 768

    result = await local_client.embed("Text")

    assert len(result) == 768
    local_client.provider.embed.assert_called_once_with("Text")


@pytest.mark.asyncio
async def test_local_client_generate_title(local_client):
    """Test that generate_title uses fast model with low temperature."""
    local_client.provider = AsyncMock()
    local_client.provider.generate.return_value = "ML Prerequisites"

    result = await local_client.generate_title("Summarize this chat")

    assert result == "ML Prerequisites"
    local_client.provider.generate.assert_called_once_with(
        "Summarize this chat",
        temperature=0.3,
        max_tokens=50,
        fast_model=True,
    )


@pytest.mark.asyncio
async def test_local_client_generate_memory(local_client):
    """Test that generate_memory uses fast model with low temperature."""
    local_client.provider = AsyncMock()
    local_client.provider.generate.return_value = "- User likes ML\n- Prefers Lab 3"

    result = await local_client.generate_memory("Synthesize this")

    assert "ML" in result
    local_client.provider.generate.assert_called_once_with(
        "Synthesize this",
        temperature=0.2,
        max_tokens=1024,
        fast_model=True,
    )


@pytest.mark.asyncio
async def test_local_client_generate_stream(local_client):
    """Test that generate_stream yields chunks from the provider."""
    async def mock_stream(*args, **kwargs):
        yield "Chunk 1"
        yield "Chunk 2"

    local_client.provider.generate_stream = mock_stream

    chunks = []
    async for chunk in local_client.generate_stream("Test"):
        chunks.append(chunk)

    assert chunks == ["Chunk 1", "Chunk 2"]


# ── Model Selection Tests ──────────────────────────────────────────────────


def test_pick_model_primary(ollama_client):
    """Test that _pick_model returns primary model by default."""
    assert ollama_client._pick_model(fast=False) == "llama3:70b"


def test_pick_model_fast(ollama_client):
    """Test that _pick_model returns fast model when requested."""
    assert ollama_client._pick_model(fast=True) == "llama3:8b"


def test_build_messages_with_system():
    """Test message building with system prompt."""
    msgs = OllamaClient._build_messages("Hello", "Be helpful")
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"


def test_build_messages_without_system():
    """Test message building without system prompt."""
    msgs = OllamaClient._build_messages("Hello", "")
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
