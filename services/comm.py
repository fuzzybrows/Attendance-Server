import random
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client
from settings import settings

# API credentials from settings
SENDGRID_API_KEY = settings.sendgrid_api_key
TWILIO_ACCOUNT_SID = settings.twilio_account_sid
TWILIO_AUTH_TOKEN = settings.twilio_auth_token
TWILIO_PHONE_NUMBER = settings.twilio_phone_number

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
