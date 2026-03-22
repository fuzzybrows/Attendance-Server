import random
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client
import firebase_admin
from firebase_admin import credentials, messaging
import os
from settings import settings

# API credentials from settings
SENDGRID_API_KEY = settings.sendgrid_api_key
TWILIO_ACCOUNT_SID = settings.twilio_account_sid
TWILIO_AUTH_TOKEN = settings.twilio_auth_token
TWILIO_PHONE_NUMBER = settings.twilio_phone_number
FIREBASE_CREDENTIALS_PATH = settings.firebase_credentials_path

def init_firebase():
    if not firebase_admin._apps:
        if FIREBASE_CREDENTIALS_PATH and FIREBASE_CREDENTIALS_PATH != "placeholder_firebase_path" and os.path.exists(FIREBASE_CREDENTIALS_PATH):
            try:
                cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
            except Exception as e:
                print(f"Failed to initialize Firebase: {e}")
        else:
            print("INFO: Firebase credentials not configured. Push notifications will be mocked.")

init_firebase()

def send_email_otp(to_email: str, otp: str):
    message = Mail(
        from_email='noreply@choirattendance.com',
        to_emails=to_email,
        subject='Your Choir Attendance Verification Code',
        html_content=f'<strong>Welcome! Your OTP is: {otp}</strong>')
    try:
        if SENDGRID_API_KEY == "placeholder_sendgrid_key":
            print(f"DEBUG: Would send EMAIL OTP {otp} to {to_email}")
            return True
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_sms_otp(to_phone: str, otp: str):
    try:
        if TWILIO_ACCOUNT_SID == "placeholder_twilio_sid":
            print(f"DEBUG: Would send SMS OTP {otp} to {to_phone}")
            return True
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Your Choir Attendance code is {otp}",
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone
        )
        return True
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False

def generate_otp():
    return str(random.randint(100000, 999999))

def send_reminder_email(to_email: str, member_name: str, session_title: str, role: str, session_time: str):
    message = Mail(
        from_email='noreply@choirattendance.com',
        to_emails=to_email,
        subject='Choir Attendance: Upcoming Session Reminder',
        html_content=f'''
        <p>Hi {member_name},</p>
        <p>This is a reminder that you are scheduled to serve as <strong>{role.replace("_", " ").title()}</strong> 
        for the upcoming session: <strong>{session_title}</strong>.</p>
        <p>Time: {session_time}</p>
        <p>Thank you for your service!</p>
        '''
    )
    try:
        if SENDGRID_API_KEY == "placeholder_sendgrid_key":
            print(f"DEBUG: Would send REMINDER EMAIL to {to_email} for {session_title}")
            return True
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return True
    except Exception as e:
        print(f"Error sending reminder email to {to_email}: {e}")
        return False

def send_reminder_sms(to_phone: str, member_name: str, session_title: str, role: str, session_time: str):
    if not to_phone:
        return False
    body = f"Hi {member_name}, reminder: you are scheduled for {session_title} ({session_time}) as {role.replace('_', ' ').title()}."
    try:
        if TWILIO_ACCOUNT_SID == "placeholder_twilio_sid":
            print(f"DEBUG: Would send REMINDER SMS to {to_phone}: {body}")
            return True
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=body,
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone
        )
        return True
    except Exception as e:
        print(f"Error sending reminder SMS to {to_phone}: {e}")
        return False

def send_push_notification(device_token: str, title: str, body: str):
    """
    Sends a push notification via Firebase Cloud Messaging (FCM).
    """
    if not device_token:
        return False
        
    if not firebase_admin._apps:
        print(f"DEBUG: Mocking PUSH NOTIFICATION to device {device_token} -> {title}: {body}")
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
        print(f"Error sending push notification to {device_token}: {e}")
        return False

