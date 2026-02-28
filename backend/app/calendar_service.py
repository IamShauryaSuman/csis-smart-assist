from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .config import Settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarService:
    def __init__(self, settings: Settings) -> None:
        self.calendar_id = settings.google_calendar_id
        self.token_path = settings.google_calendar_token_path

    def _get_service(self):
        if not self.calendar_id:
            raise HTTPException(status_code=500, detail="GOOGLE_CALENDAR_ID is not configured")

        try:
            credentials = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            return build("calendar", "v3", credentials=credentials)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=500,
                detail="Google Calendar token file not found",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Google Calendar client: {exc}",
            ) from exc

    @staticmethod
    def _parse_start(start_iso: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(start_iso)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
            return parsed.astimezone(timezone.utc)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid start_iso format") from exc

    def is_slot_available(self, start_iso: str, duration_minutes: int) -> dict:
        service = self._get_service()
        start_time = self._parse_start(start_iso)
        end_time = start_time + timedelta(minutes=duration_minutes)

        body = {
            "timeMin": start_time.isoformat(),
            "timeMax": end_time.isoformat(),
            "items": [{"id": self.calendar_id}],
        }

        result = service.freebusy().query(body=body).execute()
        busy_intervals = result["calendars"][self.calendar_id]["busy"]

        return {
            "calendar_id": self.calendar_id,
            "start_iso": start_time.isoformat(),
            "end_iso": end_time.isoformat(),
            "available": len(busy_intervals) == 0,
            "busy_intervals": busy_intervals,
        }

    def find_nearby_free_slots(
        self,
        start_iso: str,
        duration_minutes: int,
        window_hours: int,
        step_minutes: int | None,
    ) -> dict:
        service = self._get_service()
        start_time = self._parse_start(start_iso)

        step = step_minutes or duration_minutes
        window_start = start_time - timedelta(hours=window_hours)
        window_end = start_time + timedelta(hours=window_hours)

        free_slots: list[dict[str, str]] = []
        current = window_start

        while current + timedelta(minutes=duration_minutes) <= window_end:
            result = self.is_slot_available(current.isoformat(), duration_minutes)
            if result["available"]:
                free_slots.append(
                    {
                        "start_iso": result["start_iso"],
                        "end_iso": result["end_iso"],
                    }
                )
            current += timedelta(minutes=step)

        return {
            "calendar_id": self.calendar_id,
            "requested_start_iso": start_time.isoformat(),
            "duration_minutes": duration_minutes,
            "window_hours": window_hours,
            "free_slots": free_slots,
        }
