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


def resolve_service_account_path(service_account_path: str | None) -> Path:
    configured = Path(service_account_path) if service_account_path else None
    base_dir = Path(__file__).resolve().parents[1]

    candidates: list[Path] = []
    if configured is not None:
        if configured.is_absolute():
            candidates.append(configured)
        else:
            candidates.append((base_dir / configured).resolve())
            candidates.append(configured.resolve())

    candidates.extend(
        [
            (base_dir / "keys" / "service-account.json").resolve(),
            (base_dir / "service-account.json").resolve(),
        ],
    )

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


import re as _re


def _fix_pem_key(raw_key: str) -> str:
    """Rebuild a PEM private key to handle any level of escape mangling.

    Environment variable providers (Render, Heroku, etc.) sometimes store the
    private_key with literal ``\\n`` text, double-escaped ``\\\\n``, or other
    artefacts.  Rather than guessing the escaping, this function:
      1. Strips the PEM header/footer
      2. Removes *everything* that isn't valid base64 (A-Z, a-z, 0-9, +, /, =)
      3. Re-wraps at 64 characters with real newlines
      4. Re-adds proper PEM envelope
    """
    key = raw_key
    # Collapse every common escape variant into a newline first
    key = key.replace("\\r\\n", "\n")
    key = key.replace("\\r", "")
    key = key.replace("\\n", "\n")
    key = key.replace("\r", "")

    # Detect PEM type (PRIVATE KEY, RSA PRIVATE KEY, etc.)
    header_match = _re.search(r"-----BEGIN ([A-Z ]+)-----", key)
    pem_type = header_match.group(1) if header_match else "PRIVATE KEY"

    # Strip headers, footers, and whitespace to get raw base64
    key = _re.sub(r"-----BEGIN [A-Z ]+-----", "", key)
    key = _re.sub(r"-----END [A-Z ]+-----", "", key)
    # Remove anything that's not valid base64
    key = _re.sub(r"[^A-Za-z0-9+/=]", "", key)

    # Re-wrap at 64 characters
    lines = [key[i:i + 64] for i in range(0, len(key), 64)]
    rebuilt = (
        f"-----BEGIN {pem_type}-----\n"
        + "\n".join(lines)
        + f"\n-----END {pem_type}-----\n"
    )
    print(f"[SA-JSON] PEM rebuilt, {len(key)} base64 chars, {len(lines)} lines")
    return rebuilt


def build_google_service_account_credentials(
    settings: Settings,
    scopes: Sequence[str],
) -> service_account.Credentials | None:
    info_payload = settings.google_service_account_json
    path_payload = settings.google_service_account_path

    if not info_payload and not path_payload:
        try:
            path_payload = str(resolve_service_account_path(None))
        except FileNotFoundError:
            return None

    credentials: service_account.Credentials
    json_error: Exception | None = None

    if info_payload:
        try:
            # Render sometimes wraps env var values in extra quotes,
            # producing a double-stringified JSON.  Detect & unwrap.
            raw = info_payload.strip()
            if raw.startswith('"') or raw.startswith("'"):
                try:
                    unwrapped = json.loads(raw)
                    if isinstance(unwrapped, str):
                        raw = unwrapped
                except Exception:
                    pass

            service_account_info = json.loads(raw)

            if "private_key" in service_account_info:
                pk = service_account_info["private_key"]
                # Diagnostic: print to stdout so it always shows in Render logs
                print(f"[SA-JSON] private_key first 80 chars (repr): {pk[:80]!r}")
                pk = _fix_pem_key(pk)
                service_account_info["private_key"] = pk

            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=list(scopes),
            )

            if settings.google_calendar_subject:
                credentials = credentials.with_subject(
                    settings.google_calendar_subject)

            return credentials
        except Exception as exc:
            import logging
            logging.getLogger("google_client").error(
                "[SA-JSON] Failed to parse service account JSON: %s", exc,
                exc_info=True,
            )
            json_error = exc

    try:
        service_account_path = resolve_service_account_path(path_payload)
        credentials = service_account.Credentials.from_service_account_file(
            str(service_account_path),
            scopes=list(scopes),
        )
    except FileNotFoundError as exc:
        if json_error is not None:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Invalid GOOGLE_SERVICE_ACCOUNT_JSON: {json_error}. "
                    f"Also failed to find a usable service account file: {exc}"
                ),
            ) from exc
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        if json_error is not None:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Invalid GOOGLE_SERVICE_ACCOUNT_JSON: {json_error}. "
                    f"Failed to initialize Google service account credentials from file: {exc}"
                ),
            ) from exc
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
