import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

import sys
import os

# Add api to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))



@pytest.fixture
def client():
    """Returns a FastAPI TestClient."""
    from main import app
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_supabase():
    """Mocks the Supabase client with chainable methods."""
    with patch("core.database.get_supabase_client") as mock:
        client_mock = MagicMock()
        
        # Make the table() method return a mock that chains properly
        table_mock = MagicMock()
        select_mock = MagicMock()
        eq_mock = MagicMock()
        insert_mock = MagicMock()
        update_mock = MagicMock()
        
        client_mock.table.return_value = table_mock
        
        table_mock.select.return_value = select_mock
        table_mock.insert.return_value = insert_mock
        table_mock.update.return_value = update_mock
        
        select_mock.eq.return_value = eq_mock
        select_mock.order.return_value = select_mock
        select_mock.limit.return_value = select_mock
        select_mock.single.return_value = select_mock
        
        update_mock.eq.return_value = eq_mock
        
        eq_mock.eq.return_value = eq_mock
        eq_mock.order.return_value = eq_mock
        eq_mock.limit.return_value = eq_mock
        eq_mock.single.return_value = eq_mock
        
        mock.return_value = client_mock
        yield client_mock

@pytest.fixture
def mock_gemini():
    """Mocks the Gemini AI client."""
    with patch("services.llm.gemini.get_gemini_client") as mock:
        gemini_mock = AsyncMock()
        mock.return_value = gemini_mock
        yield gemini_mock

@pytest.fixture
def mock_calendar():
    """Mocks the Google Calendar service."""
    with patch("services.calendar.create_calendar_event", new_callable=AsyncMock) as mock:
        yield mock
