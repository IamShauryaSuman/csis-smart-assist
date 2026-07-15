"""
Gmail API email notification service.

Routes transactional emails through the Gmail API using an OAuth2 Refresh Token.
Supports booking status notifications and general administrative alerts.
"""

from __future__ import annotations

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import lru_cache

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from core.config import get_settings

logger = logging.getLogger(__name__)


def _build_booking_status_html(
    user_name: str,
    booking_title: str,
    description: str,
    room_name: str,
    start_time: str,
    end_time: str,
    status: str,
    admin_notes: str = "",
) -> str:
    """Build an HTML email body for booking status notifications.

    HTML templates are constructed here for server-side emails; the Next.js
    frontend handles React Email rendering for client-initiated notifications.
    """
    status_color = {
        "approved": "#22c55e",
        "rejected": "#ef4444",
        "pending": "#f59e0b",
    }.get(status, "#6b7280")

    status_label = status.upper()

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            /* Fallback styles for clients that support it */
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background-color: #0a0a0a;
                color: #e5e5e5;
                margin: 0;
                padding: 0;
            }}
        </style>
    </head>
    <body style="margin: 0; padding: 0; background-color: #0a0a0a; color: #e5e5e5; -webkit-font-smoothing: antialiased;">
        <!-- Outer wrapper for webmail clients that strip body background -->
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #0a0a0a; width: 100%; height: 100%;">
            <tr>
                <td align="center" style="padding: 40px 16px; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; color: #e5e5e5;">
                    <div style="max-width: 560px; margin: 0 auto; text-align: left;">
                        <div style="font-family: 'Space Grotesk', sans-serif; font-size: 20px; font-weight: 700; color: #ffffff; margin-bottom: 8px;">CSIS SmartAssist</div>
                        <div style="font-size: 13px; color: #737373; margin-bottom: 32px; letter-spacing: 0.05em; text-transform: uppercase;">Booking Status Update</div>
                        
                        <div style="background-color: #171717; border: 1px solid #262626; border-radius: 8px; padding: 24px; margin-bottom: 24px;">
                            <div style="display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; letter-spacing: 0.1em; color: #000000; background-color: {status_color}; margin-bottom: 16px;">
                                {status_label}
                            </div>
                            <p style="font-size: 14px; color: #e5e5e5; margin-bottom: 24px; line-height: 1.5; margin-top: 0;">
                                Hi <span style="color: #ffffff;">{user_name}</span>, your booking request has been <strong style="color: #ffffff;">{status}</strong>.
                            </p>
                            
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 8px 0; font-size: 12px; color: #737373; text-transform: uppercase; letter-spacing: 0.05em; width: 80px;">Title</td>
                                    <td style="padding: 8px 0; font-size: 14px; color: #e5e5e5;">{booking_title}</td>
                                </tr>
                                {f'''
                                <tr>
                                    <td style="padding: 8px 0; font-size: 12px; color: #737373; text-transform: uppercase; letter-spacing: 0.05em; vertical-align: top;">Desc</td>
                                    <td style="padding: 8px 0; font-size: 14px; color: #e5e5e5; line-height: 1.4;">{description}</td>
                                </tr>
                                ''' if description else ''}
                                <tr>
                                    <td style="padding: 8px 0; font-size: 12px; color: #737373; text-transform: uppercase; letter-spacing: 0.05em;">Room</td>
                                    <td style="padding: 8px 0; font-size: 14px; color: #e5e5e5;">{room_name}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; font-size: 12px; color: #737373; text-transform: uppercase; letter-spacing: 0.05em;">Start</td>
                                    <td style="padding: 8px 0; font-size: 14px; color: #e5e5e5;">{start_time}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; font-size: 12px; color: #737373; text-transform: uppercase; letter-spacing: 0.05em;">End</td>
                                    <td style="padding: 8px 0; font-size: 14px; color: #e5e5e5;">{end_time}</td>
                                </tr>
                            </table>
                            
                            {"<div style='margin-top: 24px; padding: 16px; background-color: #0a0a0a; border-left: 3px solid " + status_color + "; font-size: 13px; color: #a3a3a3; line-height: 1.5;'><strong style='color: #e5e5e5;'>Admin Notes:</strong> " + admin_notes + "</div>" if admin_notes else ""}
                        </div>
                        
                        <div style="font-size: 11px; color: #525252; text-align: center; margin-top: 32px; line-height: 1.5;">
                            CSIS Department &mdash; BITS Pilani, K K Birla Goa Campus<br>
                            This is an automated notification from CSIS SmartAssist.
                        </div>
                    </div>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


async def send_booking_notification(
    to_email: str,
    user_name: str,
    booking_title: str,
    description: str,
    room_name: str,
    start_time: str,
    end_time: str,
    status: str,
    admin_notes: str = "",
) -> bool:
    """Send a booking status notification email via Gmail API.

    Args:
        to_email: Recipient email address.
        user_name: Recipient's display name.
        booking_title: Title of the booking.
        description: Description/purpose of the booking.
        room_name: Name of the room.
        start_time: Formatted start time string.
        end_time: Formatted end time string.
        status: One of 'pending', 'approved', 'rejected'.
        admin_notes: Optional admin notes.

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    settings = get_settings()

    html = _build_booking_status_html(
        user_name=user_name,
        booking_title=booking_title,
        description=description,
        room_name=room_name,
        start_time=start_time,
        end_time=end_time,
        status=status,
        admin_notes=admin_notes,
    )

    try:
        credentials = Credentials(
            token=None,
            refresh_token=settings.gmail_refresh_token,
            client_id=settings.gmail_client_id,
            client_secret=settings.gmail_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        
        message = MIMEMultipart()
        message["To"] = to_email
        message["From"] = settings.gmail_sender_address
        message["Subject"] = f"Booking {status.upper()} - {booking_title}"
        
        msg_text = MIMEText(html, "html")
        message.attach(msg_text)
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        result = service.users().messages().send(
            userId="me", 
            body={"raw": raw_message}
        ).execute()
        
        logger.info("Email sent to %s — Gmail ID: %s", to_email, result.get("id"))
        return True

    except Exception:
        logger.exception("Failed to send booking notification to %s", to_email)
        return False


def _build_admin_new_booking_html(
    requester_name: str,
    booking_title: str,
    description: str,
    room_name: str,
    start_time: str,
    end_time: str,
) -> str:
    """Build an HTML email body for admin new booking notifications."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            /* Fallback styles for clients that support it */
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background-color: #0a0a0a;
                color: #e5e5e5;
                margin: 0;
                padding: 0;
            }}
        </style>
    </head>
    <body style="margin: 0; padding: 0; background-color: #0a0a0a; color: #e5e5e5; -webkit-font-smoothing: antialiased;">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #0a0a0a; width: 100%; height: 100%;">
            <tr>
                <td align="center" style="padding: 40px 16px; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; color: #e5e5e5;">
                    <div style="max-width: 560px; margin: 0 auto; text-align: left;">
                        <div style="font-family: 'Space Grotesk', sans-serif; font-size: 20px; font-weight: 700; color: #ffffff; margin-bottom: 8px;">CSIS SmartAssist</div>
                        <div style="font-size: 13px; color: #737373; margin-bottom: 32px; letter-spacing: 0.05em; text-transform: uppercase;">Action Required</div>
                        
                        <div style="background-color: #171717; border: 1px solid #262626; border-radius: 8px; padding: 24px; margin-bottom: 24px;">
                            <div style="display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; letter-spacing: 0.1em; color: #000000; background-color: #f59e0b; margin-bottom: 16px;">
                                NEW REQUEST
                            </div>
                            <p style="font-size: 14px; color: #e5e5e5; margin-bottom: 24px; line-height: 1.5; margin-top: 0;">
                                <strong style="color: #ffffff;">{requester_name}</strong> has submitted a new booking request that requires admin approval.
                            </p>
                            
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 8px 0; font-size: 12px; color: #737373; text-transform: uppercase; letter-spacing: 0.05em; width: 80px;">Title</td>
                                    <td style="padding: 8px 0; font-size: 14px; color: #e5e5e5;">{booking_title}</td>
                                </tr>
                                {f'''
                                <tr>
                                    <td style="padding: 8px 0; font-size: 12px; color: #737373; text-transform: uppercase; letter-spacing: 0.05em; vertical-align: top;">Desc</td>
                                    <td style="padding: 8px 0; font-size: 14px; color: #e5e5e5; line-height: 1.4;">{description}</td>
                                </tr>
                                ''' if description else ''}
                                <tr>
                                    <td style="padding: 8px 0; font-size: 12px; color: #737373; text-transform: uppercase; letter-spacing: 0.05em;">Room</td>
                                    <td style="padding: 8px 0; font-size: 14px; color: #e5e5e5;">{room_name}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; font-size: 12px; color: #737373; text-transform: uppercase; letter-spacing: 0.05em;">Start</td>
                                    <td style="padding: 8px 0; font-size: 14px; color: #e5e5e5;">{start_time}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; font-size: 12px; color: #737373; text-transform: uppercase; letter-spacing: 0.05em;">End</td>
                                    <td style="padding: 8px 0; font-size: 14px; color: #e5e5e5;">{end_time}</td>
                                </tr>
                            </table>
                        </div>
                        
                        <div style="font-size: 11px; color: #525252; text-align: center; margin-top: 32px; line-height: 1.5;">
                            CSIS Department &mdash; BITS Pilani, K K Birla Goa Campus<br>
                            This is an automated notification from CSIS SmartAssist.
                        </div>
                    </div>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

async def send_admin_new_booking_notification(
    admin_emails: list[str],
    requester_name: str,
    booking_title: str,
    description: str,
    room_name: str,
    start_time: str,
    end_time: str,
) -> bool:
    """Send a new booking notification email to admins via Gmail API."""
    if not admin_emails:
        return False
        
    settings = get_settings()

    html = _build_admin_new_booking_html(
        requester_name=requester_name,
        booking_title=booking_title,
        description=description,
        room_name=room_name,
        start_time=start_time,
        end_time=end_time,
    )

    try:
        credentials = Credentials(
            token=None,
            refresh_token=settings.gmail_refresh_token,
            client_id=settings.gmail_client_id,
            client_secret=settings.gmail_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        
        message = MIMEMultipart()
        # Join admin emails or use BCC if preferred, but for now we'll put them in To.
        message["To"] = ", ".join(admin_emails)
        message["From"] = settings.gmail_sender_address
        message["Subject"] = f"ACTION REQUIRED: New Booking Request - {booking_title}"
        
        msg_text = MIMEText(html, "html")
        message.attach(msg_text)
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        result = service.users().messages().send(
            userId="me", 
            body={"raw": raw_message}
        ).execute()
        
        logger.info("Admin notification sent to %s — Gmail ID: %s", admin_emails, result.get("id"))
        return True

    except Exception:
        logger.exception("Failed to send admin notification to %s", admin_emails)
        return False
