import pytest
from unittest.mock import patch, MagicMock
from core.rooms import get_all_rooms, get_room_by_id, get_rooms_manifest_text, get_calendar_ids

MOCK_ROOMS = [
    {
        "id": "lab_1", 
        "name": "Computer Lab 1 (D-311)", 
        "capacity": 60, 
        "calendar_id": "csis_lab1@group.calendar.google.com",
        "type": "computer_lab"
    }
]

@pytest.fixture(autouse=True)
def mock_rooms_supabase():
    with patch("core.rooms.get_supabase_client") as mock:
        class RoomsMockTable:
            def select(self, *args, **kwargs): return self
            def eq(self, *args, **kwargs): return self
            def single(self, *args, **kwargs): return self
            def execute(self): return MagicMock(data=MOCK_ROOMS)
        
        mock.return_value.table.return_value = RoomsMockTable()
        yield mock

@pytest.mark.asyncio
async def test_get_all_rooms():
    rooms = await get_all_rooms()
    assert len(rooms) > 0
    assert "id" in rooms[0]
    assert "name" in rooms[0]
    assert "capacity" in rooms[0]

@pytest.mark.asyncio
async def test_get_room_by_id():
    # lab_1 should exist based on our seed data
    room = await get_room_by_id("lab_1")
    assert room is not None
    assert room["id"] == "lab_1"
    assert room["capacity"] == 60

@pytest.mark.asyncio
async def test_get_rooms_manifest_text():
    text = await get_rooms_manifest_text()
    assert "Computer Lab 1 (D-311)" in text
    assert "**Capacity:** 60 seats" in text

@pytest.mark.asyncio
async def test_get_calendar_ids():
    cal_ids = await get_calendar_ids()
    assert len(cal_ids) > 0
    assert "csis_lab1@group.calendar.google.com" in cal_ids
