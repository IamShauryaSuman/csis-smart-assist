import pytest
from core.prompts import CALENDAR_SYSTEM_PROMPT

def test_calendar_system_prompt_formatting():
    """Test that the calendar system prompt correctly formats with IST timezone."""
    formatted_prompt = CALENDAR_SYSTEM_PROMPT.format(
        rooms_manifest="ROOM_DATA",
        availability_data="FREE_BUSY_DATA",
        memory_context="USER_MEMORY",
        current_time_ist="2026-07-12 11:00 AM IST (Offset: +05:30)"
    )

    assert "ROOM_DATA" in formatted_prompt
    assert "FREE_BUSY_DATA" in formatted_prompt
    assert "USER_MEMORY" in formatted_prompt
    assert "2026-07-12 11:00 AM IST (Offset: +05:30)" in formatted_prompt
    assert "MUST include the +05:30 offset for IST" in formatted_prompt
