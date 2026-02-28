from datetime import timezone
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
import os

ist = ZoneInfo("Asia/Kolkata")

def is_slot_available(start_time, per, service,calenderID):
    """
    Returns True if the slot is free, False if busy
    """ 

    # 1. Normalize times to UTC
    start_time = start_time.astimezone(timezone.utc)
    end_time   = start_time + timedelta(minutes=per)

    # 2. Ask Google Calendar if anything is busy in this range
    body = {
        "timeMin": start_time.isoformat(),
        "timeMax": end_time.isoformat(),
        "items": [{"id": calenderID}]  # fixed Google account
    }

    result = service.freebusy().query(body=body).execute()

    busy_intervals = result["calendars"][calenderID]["busy"]

    # 3. Decide
    return len(busy_intervals) == 0

def find_nearby_free_slots(
    start_time,
    per,
    service,
    calendarID,
    step_minutes=None
):
    """
    Returns a list of (slot_start, slot_end) tuples
    within ±window_hours of start_time.
    """
    window_hours=3

    if step_minutes is None:
        step_minutes = per  # default: non-overlapping slots

    start_time = start_time.astimezone(timezone.utc)

    window_start = start_time - timedelta(hours=window_hours)
    window_end   = start_time + timedelta(hours=window_hours)

    free_slots = []

    current = window_start

    while current + timedelta(minutes=per) <= window_end:
        if is_slot_available(current, per, service, calendarID):
            free_slots.append(
                (current, current + timedelta(minutes=per))
            )
        current += timedelta(minutes=step_minutes)

    return free_slots

def print_slots(slots):
    if not slots:
        print("No available slots found.")
        return

    print("Available slots:")
    for i, (start, end) in enumerate(slots, start=1):
        start_ist = start.astimezone(ist)
        end_ist   = end.astimezone(ist)

        print(
            f"{i}. {start_ist.strftime('%d %b %Y, %I:%M %p')} "
            f"→ {end_ist.strftime('%I:%M %p')}"
        )

from datetime import timezone

def create_event(
    service,
    calendarID,
    start_time,
    end_time,
    title,
    description=None,
    location=None
):
    """
    Creates a Google Calendar event.
    Returns the created event.
    """

    # Normalize to UTC
    start_time = start_time.astimezone(timezone.utc)
    end_time   = end_time.astimezone(timezone.utc)

    event = {
        "summary": title,
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "UTC",
        }
    }

    if description:
        event["description"] = description
    if location:
        event["location"] = location

    created_event = service.events().insert(
        calendarId=calendarID,
        body=event
    ).execute()

    return created_event

import smtplib
from email.message import EmailMessage

EMAIL = "sapphire.csis.no.reply@gmail.com"
APP_PASSWORD = os.getenv("APP_PASSWORD")

def send_email(title, email_receiver, subject):
    msg = EmailMessage()
    msg["From"] = EMAIL
    msg["To"] = email_receiver
    msg["Subject"] = subject
    msg.set_content(title)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, APP_PASSWORD)
        server.send_message(msg)

    print(f"✅ Email sent to {email_receiver}")