from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from collections.abc import Sequence
import json

from fastapi import HTTPException
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.discovery import Resource

from app.config import Settings

GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]
GOOGLE_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
GOOGLE_GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

GOOGLE_API_SCOPES: dict[str, list[str]] = {
    "calendar": GOOGLE_CALENDAR_SCOPES,
    "drive": GOOGLE_DRIVE_SCOPES,
    "gmail": GOOGLE_GMAIL_SCOPES,
}


def resolve_token_path(token_path: str) -> Path:
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
        f"No Google OAuth token file found. Checked: {', '.join(seen)}",
    )


def resolve_service_account_path(service_account_path: str) -> Path:
    configured = Path(service_account_path)
    candidates: list[Path] = []

    if configured.is_absolute():
        candidates.append(configured)
    else:
        base_dir = Path(__file__).resolve().parents[1]
        candidates.append((base_dir / configured).resolve())
        candidates.append(configured.resolve())

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"No Google service account file found. Checked: {', '.join(seen)}",
    )


def build_google_service_account_credentials(
    settings: Settings,
    scopes: Sequence[str],
) -> service_account.Credentials | None:
    info_payload = settings.google_service_account_json
    path_payload = settings.google_service_account_path

    if not info_payload and not path_payload:
        return None

    credentials: service_account.Credentials

    if info_payload:
        try:
            service_account_info = json.loads(info_payload)
            # Fix: Literal "\n" strings in private_key (common in env vars) must be actual newlines
            if "private_key" in service_account_info:
                service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")
                
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=list(scopes),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid GOOGLE_SERVICE_ACCOUNT_JSON: {exc}",
            ) from exc
    else:
        try:
            service_account_path = resolve_service_account_path(
                path_payload or "")
            credentials = service_account.Credentials.from_service_account_file(
                str(service_account_path),
                scopes=list(scopes),
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed to initialize Google service account credentials "
                    f"from GOOGLE_SERVICE_ACCOUNT_PATH: {exc}"
                ),
            ) from exc

    if settings.google_calendar_subject:
        credentials = credentials.with_subject(
            settings.google_calendar_subject)

    return credentials


def build_google_credentials(
    settings: Settings,
    scopes: Sequence[str] | None = None,
) -> Credentials:
    """Build OAuth credentials for the requested Google API scopes."""
    effective_scopes = list(scopes or GOOGLE_CALENDAR_SCOPES)

    if settings.google_refresh_token and settings.google_client_id:
        # Let Google use the refresh token's originally granted scopes.
        # For some tokens, sending an explicit `scope` on refresh returns invalid_scope.
        return Credentials(
            token=settings.google_token,
            refresh_token=settings.google_refresh_token,
            token_uri=settings.google_token_uri,
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )

    if not settings.google_token_path:
        raise FileNotFoundError(
            "Google OAuth credentials are not configured. "
            "Set GOOGLE_REFRESH_TOKEN + GOOGLE_CLIENT_ID env vars, "
            "or set GOOGLE_TOKEN_PATH to a token JSON file.",
        )

    token_path = resolve_token_path(settings.google_token_path)
    return Credentials.from_authorized_user_file(str(token_path), effective_scopes)


def get_google_service(settings: Settings, api: str, version: str) -> Resource:
    try:
        scopes = GOOGLE_API_SCOPES.get(api, GOOGLE_CALENDAR_SCOPES)
        credentials = build_google_credentials(
            settings=settings, scopes=scopes)
        return build(api, version, credentials=credentials)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize Google {api} client: {exc}",
        ) from exc


def get_google_calendar_client(settings: Settings) -> tuple[Resource, str]:
    if not settings.google_calendar_id:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CALENDAR_ID is not configured",
        )

    service_account_credentials = build_google_service_account_credentials(
        settings=settings,
        scopes=GOOGLE_CALENDAR_SCOPES,
    )
    if service_account_credentials is not None:
        service = build("calendar", "v3",
                        credentials=service_account_credentials)
    else:
        service = get_google_service(
            settings=settings, api="calendar", version="v3")
    calendar_id = settings.google_calendar_id.strip()
    if not calendar_id or "your-calendar-id" in calendar_id.lower():
        calendar_id = "primary"

    return service, calendar_id


def get_google_drive_client(settings: Settings) -> Resource:
    service_account_credentials = build_google_service_account_credentials(
        settings=settings,
        scopes=GOOGLE_DRIVE_SCOPES,
    )
    if service_account_credentials is not None:
        return build("drive", "v3", credentials=service_account_credentials)
    return get_google_service(settings=settings, api="drive", version="v3")


def get_google_gmail_client(settings: Settings) -> Resource:
    return get_google_service(settings=settings, api="gmail", version="v1")


def parse_start_iso(start_iso: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(start_iso)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
        return parsed.astimezone(timezone.utc)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail="Invalid start_iso format") from exc
