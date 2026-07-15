import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from services.llm.hybrid import HybridLLMClient

@pytest.fixture
def mock_gemini():
    mock = AsyncMock()
    mock.__class__.__name__ = "GeminiClient"
    return mock

@pytest.fixture
def mock_groq():
    mock = AsyncMock()
    mock.__class__.__name__ = "OpenAICompatibleClient"
    mock._client.base_url = "https://api.groq.com/openai/v1"
    return mock

@pytest.fixture
def mock_openrouter():
    mock = AsyncMock()
    mock.__class__.__name__ = "OpenAICompatibleClient"
    mock._client.base_url = "https://openrouter.ai/api/v1"
    return mock

@pytest.fixture
def hybrid_client(mock_gemini, mock_groq, mock_openrouter):
    with patch("services.llm.hybrid.GeminiClient", return_value=mock_gemini), \
         patch("services.llm.hybrid.OpenAICompatibleClient", side_effect=[mock_groq, mock_openrouter]):
        client = HybridLLMClient()
        return client

@pytest.mark.asyncio
async def test_generate_success_primary(hybrid_client, mock_gemini, mock_groq, mock_openrouter):
    """Test that generate() succeeds using the primary provider (Gemini)."""
    mock_gemini.generate.return_value = "Gemini response"
    
    response = await hybrid_client.generate("Test prompt")
    
    assert response == "Gemini response"
    mock_gemini.generate.assert_called_once()
    mock_groq.generate.assert_not_called()
    mock_openrouter.generate.assert_not_called()

@pytest.mark.asyncio
async def test_generate_fallback_to_groq(hybrid_client, mock_gemini, mock_groq, mock_openrouter):
    """Test that generate() falls back to Groq if Gemini throws a 429."""
    mock_gemini.generate.side_effect = Exception("429 Rate limit exceeded")
    mock_groq.generate.return_value = "Groq response"
    
    response = await hybrid_client.generate("Test prompt")
    
    assert response == "Groq response"
    mock_gemini.generate.assert_called_once()
    mock_groq.generate.assert_called_once()
    mock_openrouter.generate.assert_not_called()

@pytest.mark.asyncio
async def test_generate_fallback_all_exhausted(hybrid_client, mock_gemini, mock_groq, mock_openrouter):
    """Test that generate() raises an exception if all providers fail."""
    mock_gemini.generate.side_effect = Exception("429 Rate limit")
    mock_groq.generate.side_effect = Exception("500 Server Error")
    mock_openrouter.generate.side_effect = Exception("503 Service Unavailable")
    
    with pytest.raises(Exception, match="503 Service Unavailable"):
        await hybrid_client.generate("Test prompt")
    
    mock_gemini.generate.assert_called_once()
    mock_groq.generate.assert_called_once()
    mock_openrouter.generate.assert_called_once()

@pytest.mark.asyncio
async def test_generate_json_primary(hybrid_client, mock_gemini, mock_groq, mock_openrouter):
    """Test that generate_json() uses Groq as primary."""
    mock_groq.generate_json.return_value = {"intent": "calendar"}
    
    response = await hybrid_client.generate_json("Test prompt")
    
    assert response == {"intent": "calendar"}
    mock_groq.generate_json.assert_called_once()
    mock_gemini.generate_json.assert_not_called()

@pytest.mark.asyncio
async def test_generate_stream_fallback(hybrid_client, mock_gemini, mock_groq):
    """Test that generate_stream falls back correctly on connection error."""
    
    # Setup Gemini to fail IMMEDIATELY when the async generator is iterated
    async def failing_stream(*args, **kwargs):
        raise Exception("Quota exceeded")
        yield "Never reached"
        
    async def succeeding_stream(*args, **kwargs):
        yield "Chunk 1"
        yield "Chunk 2"
        
    # Bypass the AsyncMock logic which incorrectly tries to await async generators
    hybrid_client.gemini.generate_stream = failing_stream
    hybrid_client.groq.generate_stream = succeeding_stream
    
    chunks = []
    async for chunk in hybrid_client.generate_stream("Test"):
        chunks.append(chunk)
        
    assert chunks == ["Chunk 1", "Chunk 2"]
