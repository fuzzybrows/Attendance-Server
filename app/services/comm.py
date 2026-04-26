import logging
import random

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client
import firebase_admin
from firebase_admin import credentials, messaging
import os
from app.settings import settings

logger = logging.getLogger(__name__)

# API credentials from settings
SENDGRID_API_KEY = settings.sendgrid_api_key
TWILIO_ACCOUNT_SID = settings.twilio_account_sid
TWILIO_AUTH_TOKEN = settings.twilio_auth_token
TWILIO_PHONE_NUMBER = settings.twilio_phone_number
FIREBASE_CREDENTIALS_PATH = settings.firebase_credentials_path
EMAIL_FROM_ADDRESS = settings.email_from_address
ROLE_PREPOSITION = settings.role_preposition

def init_firebase():
    if not firebase_admin._apps:
        if FIREBASE_CREDENTIALS_PATH and FIREBASE_CREDENTIALS_PATH != "placeholder_firebase_path" and os.path.exists(FIREBASE_CREDENTIALS_PATH):
            try:
                cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
            except Exception as e:
                logger.error(f"Failed to initialize Firebase: {e}", exc_info=True, extra={"type": "firebase_init_error"})
        else:
            logger.info("Firebase credentials not configured. Push notifications will be mocked.", extra={"type": "firebase_init_skip"})

init_firebase()

def send_email_otp(to_email: str, otp: str):
    message = Mail(
        from_email=EMAIL_FROM_ADDRESS,
        to_emails=to_email,
        subject='Your Verification Code',
        plain_text_content=f'Welcome! Your verification code is: {otp}\n\nPlease enter this code to complete your verification. This code will expire shortly.\n\nIf you did not request this code, you can safely ignore this email. No changes will be made to your account.\n\nThank you.',
        html_content=f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;line-height:1.6;padding:20px;">
    <h2>Verification Code</h2>
    <p>Welcome! Your verification code is:</p>
    <p style="font-size:24px;font-weight:bold;letter-spacing:4px;padding:12px;text-align:center;">{otp}</p>
    <p>Please enter this code to complete your verification. This code will expire shortly.</p>
    <p>If you did not request this code, you can safely ignore this email. No changes will be made to your account.</p>
    <p>Thank you for using our service.</p>
    <p style="font-size:12px;color:#999;">This is an automated message. Please do not reply to this email.</p>
</body>
</html>''')
    try:
        if SENDGRID_API_KEY == "placeholder_sendgrid_key":
            logger.debug(f"Would send EMAIL OTP {otp} to {to_email}", extra={"type": "email_otp_mock", "to_email": to_email})
            return True
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return True
    except Exception as e:
        logger.error(f"Error sending email: {e}", exc_info=True, extra={"type": "email_otp_error", "to_email": to_email})
        return False

def send_sms_otp(to_phone: str, otp: str):
    try:
        if TWILIO_ACCOUNT_SID == "placeholder_twilio_sid":
            logger.debug(f"Would send SMS OTP {otp} to {to_phone}", extra={"type": "sms_otp_mock", "to_phone": to_phone})
            return True
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Your verification code is {otp}",
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone
        )
        return True
    except Exception as e:
        logger.error(f"Error sending SMS: {e}", exc_info=True, extra={"type": "sms_otp_error", "to_phone": to_phone})
        return False

def generate_otp():
    return str(random.randint(100000, 999999))

def send_reminder_email(to_email: str, member_name: str, session_title: str, role: str, session_time: str):
    role_display = role.replace("_", " ").title()
    message = Mail(
        from_email=EMAIL_FROM_ADDRESS,
        to_emails=to_email,
        subject='Upcoming Session Reminder',
        plain_text_content=f'Hi {member_name},\n\nThis is a reminder that you are scheduled to serve {ROLE_PREPOSITION} {role_display} for the upcoming session: {session_title}.\n\nSession: {session_title}\nRole: {role_display}\nTime: {session_time}\n\nPlease arrive on time and be prepared for your role. Thank you for your service and dedication!\n\nIf you have any questions or need to make changes, please contact your team lead.',
        html_content=f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;line-height:1.6;padding:20px;">
    <h2>Upcoming Session Reminder</h2>
    <p>Hi {member_name},</p>
    <p>This is a reminder that you are scheduled to serve {ROLE_PREPOSITION} <strong>{role_display}</strong>
    for the upcoming session: <strong>{session_title}</strong>.</p>
    <p><strong>Session:</strong> {session_title}<br>
    <strong>Role:</strong> {role_display}<br>
    <strong>Time:</strong> {session_time}</p>
    <p>Please arrive on time and be prepared for your role. Thank you for your service and dedication!</p>
    <p>If you have any questions or need to make changes, please contact your team lead.</p>
    <p style="font-size:12px;color:#999;">This is an automated message. Please do not reply to this email.</p>
</body>
</html>''')
    try:
        if SENDGRID_API_KEY == "placeholder_sendgrid_key":
            logger.debug(f"Would send REMINDER EMAIL to {to_email} for {session_title}", extra={"type": "reminder_email_mock", "to_email": to_email, "session_title": session_title})
            return True
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return True
    except Exception as e:
        logger.error(f"Error sending reminder email to {to_email}: {e}", exc_info=True, extra={"type": "reminder_email_error", "to_email": to_email, "session_title": session_title})
        return False

def send_reminder_sms(to_phone: str, member_name: str, session_title: str, role: str, session_time: str):
    if not to_phone:
        return False
    body = f"Hi {member_name}, reminder: you are scheduled for {session_title} ({session_time}) {ROLE_PREPOSITION} {role.replace('_', ' ').title()}."
    try:
        if TWILIO_ACCOUNT_SID == "placeholder_twilio_sid":
            logger.debug(f"Would send REMINDER SMS to {to_phone}: {body}", extra={"type": "reminder_sms_mock", "to_phone": to_phone, "session_title": session_title})
            return True
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=body,
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone
        )
        return True
    except Exception as e:
        logger.error(f"Error sending reminder SMS to {to_phone}: {e}", exc_info=True, extra={"type": "reminder_sms_error", "to_phone": to_phone, "session_title": session_title})
        return False

def send_push_notification(device_token: str, title: str, body: str):
    """
    Sends a push notification via Firebase Cloud Messaging (FCM).
    """
    if not device_token:
        return False
        
    if not firebase_admin._apps:
        logger.debug(f"Mocking PUSH NOTIFICATION to device {device_token} -> {title}: {body}", extra={"type": "push_notification_mock", "device_token": device_token, "title": title})
        return True
        
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=device_token,
        )
        response = messaging.send(message)
        return True
    except Exception as e:
        logger.error(f"Error sending push notification to {device_token}: {e}", exc_info=True, extra={"type": "push_notification_error", "device_token": device_token, "title": title})
        return False

