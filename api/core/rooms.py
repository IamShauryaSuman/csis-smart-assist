"""
Dynamic room/lab manifest for the CSIS Department.

This module fetches all bookable spaces with their capabilities,
hardware profiles, and capacity from the database. The LLM uses this to suggest alternatives
when a requested room is unavailable.

Each room's `calendar_id` maps to a Google Calendar resource.
"""

from __future__ import annotations

from core.database import get_supabase_client

async def get_all_rooms() -> list[dict]:
    """Fetch all rooms from the database."""
    supabase = get_supabase_client()
    response = supabase.table("rooms").select("*").execute()
    return response.data

async def get_rooms_manifest_text() -> str:
    """Format the rooms manifest as a human-readable text block for LLM context."""
    rooms = await get_all_rooms()
    lines: list[str] = []
    for room in rooms:
        lines.append(f"### {room['name']} (ID: {room['id']})")
        lines.append(f"- **Type:** {room['type'].replace('_', ' ').title()}")
        lines.append(f"- **Capacity:** {room['capacity']} seats")
        
        hardware = room.get('hardware', [])
        lines.append(f"- **Hardware:** {', '.join(hardware)}")
        
        desc = room.get('description', '')
        lines.append(f"- **Description:** {desc}")
        lines.append("")
    return "\n".join(lines)

async def get_room_by_id(room_id: str) -> dict | None:
    """Look up a room by its ID from the database."""
    supabase = get_supabase_client()
    response = supabase.table("rooms").select("*").eq("id", room_id).execute()
    data = response.data
    if data and len(data) > 0:
        return data[0]
    return None

async def get_calendar_ids() -> list[str]:
    """Return all Google Calendar IDs for FreeBusy queries."""
    supabase = get_supabase_client()
    response = supabase.table("rooms").select("calendar_id").execute()
    return [room["calendar_id"] for room in response.data]
