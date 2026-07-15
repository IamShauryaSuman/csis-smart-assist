import pytest
from unittest.mock import patch, MagicMock, AsyncMock

USER_ID = "11111111-1111-1111-1111-111111111111"
SESSION_ID = "22222222-2222-2222-2222-222222222222"

@pytest.fixture
def chat_mock_supabase(mock_supabase):
    with patch("routes.chat.get_supabase_client", return_value=mock_supabase):
        yield mock_supabase

USER_ID = "11111111-1111-1111-1111-111111111111"
SESSION_ID = "22222222-2222-2222-2222-222222222222"

def test_chat_send_unauthenticated(client):
    """Test that the chat endpoint rejects unauthenticated requests."""
    response = client.post("/api/chat/send", json={
        "session_id": SESSION_ID,
        "message": "Hello"
    })
    assert response.status_code in (401, 403, 422)

def test_create_session(client, chat_mock_supabase):
    chat_mock_supabase.table().insert().execute.return_value = MagicMock(data=[{
        "id": SESSION_ID, "user_id": USER_ID, "title": "New Chat",
        "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z"
    }])
    
    with patch("routes.chat._extract_user_id", return_value=USER_ID):
        response = client.post("/api/chat/sessions", json={"title": "Test Chat"}, headers={"Authorization": "Bearer token"})
    
    assert response.status_code == 200
    assert response.json()["id"] == SESSION_ID

def test_get_sessions(client, chat_mock_supabase):
    chat_mock_supabase.table().select().eq().order().execute.return_value = MagicMock(data=[{
        "id": SESSION_ID, "user_id": USER_ID, "title": "New Chat",
        "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z"
    }])
    
    with patch("routes.chat._extract_user_id", return_value=USER_ID):
        response = client.get("/api/chat/sessions", headers={"Authorization": "Bearer token"})
    
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_chat_send_general_query(client, chat_mock_supabase, mock_gemini):
    # Mock parallel DB queries inside _fetch_db_data
    chat_mock_supabase.table().select().eq().single().execute.side_effect = [
        MagicMock(data={"id": SESSION_ID, "user_id": USER_ID}), # session
        MagicMock(data={"full_name": "Test User"}), # profile
        MagicMock(data=[]), # history
    ]
    
    # Mock LLM intent
    mock_gemini.generate_json = AsyncMock(return_value={"intent": "general_query", "confidence": 0.95})
    
    # Mock LLM streaming
    async def mock_stream(*args, **kwargs):
        yield "Hello "
        yield "World"
        
    mock_gemini.generate_stream = mock_stream
    mock_gemini.generate_title = AsyncMock(return_value="Test Title")
    
    # Mock Hybrid client
    with patch("routes.chat.get_hybrid_client", return_value=mock_gemini), patch("routes.chat._extract_user_id", return_value=USER_ID):
        response = client.post("/api/chat/send", json={
            "session_id": SESSION_ID,
            "message": "Hi"
        }, headers={"Authorization": "Bearer token"})
    
    assert response.status_code == 200
    text = response.text
    assert '"intent": "general_query"' in text
    assert '"text": "Hello "' in text
    assert '"text": "World"' in text
    assert '"type": "done"' in text

def test_chat_send_calendar_query(client, chat_mock_supabase, mock_gemini):
    # Mock parallel DB queries
    chat_mock_supabase.table().select().eq().single().execute.side_effect = [
        MagicMock(data={"id": SESSION_ID, "user_id": USER_ID}), # session
        MagicMock(data={}), # profile
        MagicMock(data=[]), # history
    ]
    
    mock_gemini.generate_json = AsyncMock(return_value={"intent": "calendar_query"})
    
    # Calendar doesn't stream, it uses generate
    mock_gemini.generate = AsyncMock(return_value="Sure, here is the proposal.\n```booking_proposal\n{\"room_id\": \"1\"}\n```")
    mock_gemini.generate_title = AsyncMock(return_value="Test Title")
    
    with patch("routes.chat.query_freebusy", new_callable=AsyncMock) as mock_fb, \
         patch("routes.chat.format_availability_for_llm", new_callable=AsyncMock) as mock_fmt, \
         patch("routes.chat.get_rooms_manifest_text", new_callable=AsyncMock) as mock_manifest, \
         patch("routes.chat.get_hybrid_client", return_value=mock_gemini), \
         patch("routes.chat._extract_user_id", return_value=USER_ID):
        
        mock_fb.return_value = {}
        mock_fmt.return_value = ""
        mock_manifest.return_value = ""
        
        response = client.post("/api/chat/send", json={
            "session_id": SESSION_ID,
            "message": "Book a room"
        }, headers={"Authorization": "Bearer token"})
        
    assert response.status_code == 200
    text = response.text
    assert '"interactive_type": "booking_proposal"' in text
    assert '"interactive_payload": {"room_id": "1"}' in text
    assert '"text": "Sure, here is the proposal."' in text

def test_chat_send_rate_limit(client, chat_mock_supabase, mock_gemini):
    chat_mock_supabase.table().select().eq().single().execute.return_value = MagicMock(data={"id": SESSION_ID, "user_id": USER_ID})
    
    # Simulate Quota exceeded
    mock_gemini.generate_json.side_effect = Exception("429 ResourceExhausted")
    
    with patch("routes.chat.get_hybrid_client", return_value=mock_gemini), patch("routes.chat._extract_user_id", return_value=USER_ID):
        response = client.post("/api/chat/send", json={
            "session_id": SESSION_ID,
            "message": "Hi"
        }, headers={"Authorization": "Bearer token"})
    
    assert response.status_code == 429
    assert "LLM Rate limit exceeded" in response.json()["detail"]

def test_get_session_messages(client, chat_mock_supabase):
    chat_mock_supabase.table().select().eq().single().execute.side_effect = [
        MagicMock(data={"user_id": USER_ID}),
        MagicMock(data=[{"id": "msg-1", "session_id": SESSION_ID, "role": "user", "content": "Hello", "created_at": "2023-01-01T00:00:00Z"}])
    ]
    
    with patch("routes.chat._extract_user_id", return_value=USER_ID):
        response = client.get(f"/api/chat/sessions/{SESSION_ID}/messages", headers={"Authorization": "Bearer token"})
        
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_delete_session(client, chat_mock_supabase):
    chat_mock_supabase.table().select().eq().single().execute.return_value = MagicMock(data={"user_id": USER_ID})
    
    with patch("routes.chat._extract_user_id", return_value=USER_ID):
        response = client.delete(f"/api/chat/sessions/{SESSION_ID}", headers={"Authorization": "Bearer token"})
        
    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}

def test_update_session(client, chat_mock_supabase):
    chat_mock_supabase.table().select().eq().single().execute.side_effect = [
        MagicMock(data={"user_id": USER_ID}),
        MagicMock(data=[{"id": SESSION_ID, "user_id": USER_ID, "title": "Updated Title", "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:01:00Z"}])
    ]
    
    with patch("routes.chat._extract_user_id", return_value=USER_ID):
        response = client.patch(f"/api/chat/sessions/{SESSION_ID}", json={"title": "Updated Title"}, headers={"Authorization": "Bearer token"})
        
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"
