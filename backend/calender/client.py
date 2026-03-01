from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import Settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _resolve_token_path(token_path: str) -> Path:
    configured = Path(token_path)
    candidates: list[Path] = []

    if configured.is_absolute():
        candidates.append(configured)
    else:
        base_dir = Path(__file__).resolve().parents[1]
        candidates.append((base_dir / configured).resolve())
        candidates.append(configured.resolve())

    if configured.name == "token.json":
        candidates.append(candidates[0].with_name("tokens.json"))
    if configured.name == "tokens.json":
        candidates.append(candidates[0].with_name("token.json"))

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"No Google Calendar token file found. Checked: {', '.join(seen)}",
    )


def get_calendar_client(settings: Settings):
    if not settings.google_calendar_id:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CALENDAR_ID is not configured",
        )

    try:
        token_path = _resolve_token_path(settings.google_calendar_token_path)
        credentials = Credentials.from_authorized_user_file(
            str(token_path),
            SCOPES,
        )
        service = build("calendar", "v3", credentials=credentials)
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

    calendar_id = settings.google_calendar_id.strip()
    if not calendar_id or "your-calendar-id" in calendar_id.lower():
        calendar_id = "primary"

    return service, calendar_id


def parse_start_iso(start_iso: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(start_iso)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
        return parsed.astimezone(timezone.utc)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail="Invalid start_iso format") from exc
