from datetime import timezone

def is_slot_available(start_time, end_time, service):
    """
    Returns True if the slot is free, False if busy
    """

    # 1. Normalize times to UTC
    start_time = start_time.astimezone(timezone.utc)
    end_time   = end_time.astimezone(timezone.utc)

    # 2. Ask Google Calendar if anything is busy in this range
    body = {
        "timeMin": start_time.isoformat(),
        "timeMax": end_time.isoformat(),
        "items": [{"id": "primary"}]  # fixed Google account
    }

    result = service.freebusy().query(body=body).execute()

    busy_intervals = result["calendars"]["primary"]["busy"]

    # 3. Decide
    return len(busy_intervals) == 0