import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from services.calendar import _get_calendar_service, create_calendar_event, query_freebusy, format_availability_for_llm

@pytest.fixture
def mock_credentials():
    with patch("services.calendar.service_account.Credentials.from_service_account_info") as mock:
        mock.return_value = MagicMock()
        yield mock

@pytest.fixture
def mock_build():
    with patch("services.calendar.build") as mock:
        service_mock = MagicMock()
        mock.return_value = service_mock
        yield service_mock

def test_get_calendar_service_missing_env():
    with patch("services.calendar.get_settings") as mock_settings:
        mock_settings.return_value.google_service_account_info = None
        with pytest.raises(RuntimeError, match="Google service account credentials not configured."):
            _get_calendar_service()

@pytest.mark.asyncio
async def test_create_calendar_event(mock_credentials, mock_build):
    events_mock = mock_build.events.return_value.insert.return_value
    events_mock.execute.return_value = {"id": "new_event_123", "htmlLink": "http://link"}
    
    with patch("services.calendar._get_calendar_service", return_value=mock_build), \
         patch("services.calendar.get_room_by_id", return_value={"id": "test_cal_id", "name": "Room", "calendar_id": "real_cal_id"}):
        from datetime import datetime
        event = await create_calendar_event(
            "test_cal_id",
            "Test Event",
            datetime(2023, 1, 1, 10),
            datetime(2023, 1, 1, 11),
            "Test Description",
            "test@example.com"
        )
    assert event is not None
    assert event["id"] == "new_event_123"
    mock_build.events.return_value.insert.assert_called_once()

@pytest.mark.asyncio
async def test_query_freebusy(mock_credentials, mock_build):
    mock_build.freebusy.return_value.query.return_value.execute.return_value = {
        "calendars": {
            "real_cal_id": {"busy": [{"start": "2023-01-01T10:00:00Z", "end": "2023-01-01T11:00:00Z"}]}
        }
    }
    
    with patch("services.calendar._get_calendar_service", return_value=mock_build), \
         patch("services.calendar.get_all_rooms", return_value=[{"id": "cal_1", "calendar_id": "real_cal_id"}]), \
         patch("services.calendar.get_calendar_ids", return_value=["real_cal_id"]):
        from datetime import datetime
        busy_data = await query_freebusy(
            datetime(2023, 1, 1),
            datetime(2023, 1, 2)
        )
    assert "cal_1" in busy_data
    assert len(busy_data["cal_1"]) == 1

@pytest.mark.asyncio
async def test_format_availability_for_llm(mock_credentials, mock_build):
    availability = {
        "room_1": [{"start": "2023-01-01T10:00:00Z", "end": "2023-01-01T11:00:00Z"}]
    }
    
    with patch("services.calendar.get_all_rooms", return_value=[{"id": "room_1", "name": "Room 1", "calendar_id": "cal_1", "type": "computer_lab"}]):
        text = await format_availability_for_llm(availability)
        
    assert "Room 1" in text
    assert "2023-01-01T10:00:00Z → 2023-01-01T11:00:00Z" in text
