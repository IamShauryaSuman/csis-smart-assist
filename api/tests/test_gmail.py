import base64
from unittest.mock import patch, MagicMock

import pytest

# We will import this once we create it
from services.gmail import send_booking_notification

@pytest.fixture
def mock_settings():
    with patch("services.gmail.get_settings") as mock:
        settings = MagicMock()
        settings.gmail_client_id = "test-client-id"
        settings.gmail_client_secret = "test-client-secret"
        settings.gmail_refresh_token = "test-refresh-token"
        settings.gmail_sender_address = "system@test.com"
        mock.return_value = settings
        yield settings

@pytest.fixture
def mock_gmail_api():
    with patch("services.gmail.build") as mock_build, \
         patch("services.gmail.Credentials") as mock_credentials:
        
        mock_creds_instance = MagicMock()
        mock_credentials.return_value = mock_creds_instance
        
        mock_service = MagicMock()
        mock_users = MagicMock()
        mock_messages = MagicMock()
        mock_send = MagicMock()
        
        mock_build.return_value = mock_service
        mock_service.users.return_value = mock_users
        mock_users.messages.return_value = mock_messages
        mock_messages.send.return_value = mock_send
        mock_send.execute.return_value = {"id": "12345"}
        
        yield mock_messages.send

@pytest.mark.asyncio
async def test_send_booking_notification(mock_settings, mock_gmail_api):
    await send_booking_notification(
        to_email="student@bits.edu",
        user_name="John Doe",
        booking_title="Study Group",
        description="Discussing physics assignment",
        room_name="Room 101",
        start_time="2023-10-10 10:00",
        end_time="2023-10-10 11:00",
        status="approved",
        admin_notes="Approved!"
    )
    
    # Assert Gmail API was called
    assert mock_gmail_api.call_count == 1
    
    # Assert the raw payload was passed to the execute method
    call_args = mock_gmail_api.call_args[1]
    assert "userId" in call_args
    assert call_args["userId"] == "me"
    assert "body" in call_args
    assert "raw" in call_args["body"]
    
    import email
    
    # Decode the raw base64 payload to ensure it looks like an email
    raw_payload = call_args["body"]["raw"]
    decoded_raw = base64.urlsafe_b64decode(raw_payload.encode("utf-8")).decode("utf-8")
    
    msg = email.message_from_string(decoded_raw)
    assert msg["To"] == "student@bits.edu"
    assert msg["Subject"] == "Booking APPROVED - Study Group"
    
    # Parse the HTML payload
    payload = msg.get_payload()[0].get_payload(decode=True).decode("utf-8")
    assert "Approved!" in payload
    assert "John Doe" in payload
