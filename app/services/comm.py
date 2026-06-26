import logging
import random

# Firebase disabled to reduce bundle size — push notifications stubbed out
# import firebase_admin
# from firebase_admin import credentials, messaging
import os
from datetime import date
from app.settings import settings
from app.services.email_providers import get_email_provider
from app.services.sms_providers import get_sms_provider

# Template imports
from app.services.templates.otp import email_otp as _otp_email_template, sms_otp as _otp_sms_template
from app.services.templates.reminder import reminder_email as _reminder_email_template, reminder_sms as _reminder_sms_template
from app.services.templates.leader_summary import leader_summary as _leader_summary_template
from app.services.templates.availability_reminder import availability_reminder as _availability_reminder_template
from app.services.templates.assignment_notification import assignment_notification as _assignment_notification_template

logger = logging.getLogger(__name__)

# API credentials from settings
# FIREBASE_CREDENTIALS_PATH = settings.firebase_credentials_path
ROLE_PREPOSITION = settings.role_preposition

# Module-level provider singletons
_email_provider = get_email_provider()
_sms_provider = get_sms_provider()


def _send_email(to_email: str, subject: str, plain_text: str, html: str, attachments: list = None) -> bool:
    """Send an email using the configured provider."""
    return _email_provider.send(to_email, subject, plain_text, html, attachments)


def _send_sms(to_phone: str, body: str) -> bool:
    """Send an SMS using the configured provider."""
    return _sms_provider.send(to_phone, body)


# ── Firebase (disabled) ─────────────────────────────────────────────────────
#
# def init_firebase():
#     if not firebase_admin._apps:
#         if FIREBASE_CREDENTIALS_PATH and FIREBASE_CREDENTIALS_PATH != "placeholder_firebase_path" and os.path.exists(FIREBASE_CREDENTIALS_PATH):
#             try:
#                 cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
#                 firebase_admin.initialize_app(cred)
#             except Exception as e:
#                 logger.error(f"Failed to initialize Firebase: {e}", exc_info=True, extra={"type": "firebase_init_error"})
#         else:
#             logger.info("Firebase credentials not configured. Push notifications will be mocked.", extra={"type": "firebase_init_skip"})
#
# init_firebase()


# ── Public API ──────────────────────────────────────────────────────────────

def send_email_otp(to_email: str, otp: str):
    subject, plain_text, html = _otp_email_template(otp)
    return _send_email(to_email, subject, plain_text, html)

def send_sms_otp(to_phone: str, otp: str):
    return _send_sms(to_phone, _otp_sms_template(otp))

def generate_otp():
    return str(random.randint(100000, 999999))

def send_reminder_email(to_email: str, member_first_name: str, session_title: str, role: str, session_time: str):
    role_display = role.replace("_", " ").title()
    subject, plain_text, html = _reminder_email_template(
        member_first_name, session_title, role_display, session_time, ROLE_PREPOSITION,
    )
    return _send_email(to_email, subject, plain_text, html)

def send_reminder_sms(to_phone: str, member_name: str, session_title: str, role: str, session_time: str):
    if not to_phone:
        return False
    role_display = role.replace('_', ' ').title()
    body = _reminder_sms_template(member_name, session_title, role_display, session_time, ROLE_PREPOSITION)
    return _send_sms(to_phone, body)


def send_leader_summary_email(
    to_email: str,
    leader_name: str,
    session_title: str,
    session_time: str,
    assignments: list,       # [{"member_name": str, "role": str}, ...]
    available_members: list,  # [str, ...]  — names
    unavailable_members: list # [str, ...]  — names
):
    """Send a comprehensive session summary email to a leader/admin."""
    subject, plain_text, html = _leader_summary_template(
        leader_name, session_title, session_time,
        assignments, available_members, unavailable_members,
    )
    return _send_email(to_email, subject, plain_text, html)


def send_push_notification(device_token: str, title: str, body: str):
    """
    Push notifications via FCM — currently disabled (Firebase commented out).
    Logs the notification and returns True as a no-op stub.
    """
    if not device_token:
        return False

    # if not firebase_admin._apps:
    #     logger.debug(f"Mocking PUSH NOTIFICATION to device {device_token} -> {title}: {body}", extra={"type": "push_notification_mock", "device_token": device_token, "title": title})
    #     return True
    #
    # try:
    #     message = messaging.Message(
    #         notification=messaging.Notification(
    #             title=title,
    #             body=body,
    #         ),
    #         token=device_token,
    #     )
    #     response = messaging.send(message)
    #     return True
    # except Exception as e:
    #     logger.error(f"Error sending push notification to {device_token}: {e}", exc_info=True, extra={"type": "push_notification_error", "device_token": device_token, "title": title})
    #     return False

    logger.debug(
        f"Mocking PUSH NOTIFICATION to device {device_token} -> {title}: {body}",
        extra={"type": "push_notification_mock", "device_token": device_token, "title": title},
    )
    return True


def send_availability_reminder_email(
    to_email: str,
    member_first_name: str,
    year: int,
    month: int,
    unavailable_dates: set,
    session_dates: set,
    calendar_url: str,
):
    """
    Send a monthly availability reminder with an HTML calendar grid.

    Args:
        to_email: Formatted email address, e.g. "John Doe <john@example.com>"
        member_first_name: First name for greeting
        year: Target year
        month: Target month (1-12)
        unavailable_dates: Set of ISO date strings the member has marked unavailable
        session_dates: Set of ISO date strings that have scheduled sessions
        calendar_url: Deep-link URL to the calendar page for this month
    """
    subject, plain_text, html = _availability_reminder_template(
        member_first_name, year, month,
        unavailable_dates, session_dates, calendar_url,
    )
    return _send_email(to_email, subject, plain_text, html)


def send_assignment_notification_email(
    to_email: str,
    member_first_name: str,
    year: int,
    month: int,
    assignments: list,
    calendar_url: str,
    ics_bytes: bytes = None,
):
    """
    Send a monthly assignment notification with a calendar grid and .ics attachment.

    Args:
        to_email: Formatted email address, e.g. "John Doe <john@example.com>"
        member_first_name: First name for greeting
        year: Target year
        month: Target month (1-12)
        assignments: List of dicts with keys: session_title, role, start_time (datetime), end_time (datetime or None)
        calendar_url: Deep-link URL to the calendar page for this month
        ics_bytes: Optional .ics file content as bytes for attachment
    """
    subject, plain_text, html, email_attachments = _assignment_notification_template(
        member_first_name, year, month,
        assignments, calendar_url, ics_bytes,
    )
    return _send_email(to_email, subject, plain_text, html, email_attachments)
