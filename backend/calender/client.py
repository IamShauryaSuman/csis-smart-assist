from app.config import Settings
from app.google_client import get_google_calendar_client
from app.google_client import parse_start_iso


def get_calendar_client(settings: Settings):
    return get_google_calendar_client(settings)
