"""
Twilio Verify API service for OTP verification.
Uses Twilio's managed Verify service instead of manually sending OTPs.
"""
from twilio.rest import Client
from app.settings import settings

# Twilio API credentials from settings
TWILIO_ACCOUNT_SID = settings.twilio_account_sid
TWILIO_AUTH_TOKEN = settings.twilio_auth_token
TWILIO_VERIFY_SERVICE_SID = settings.twilio_verify_service_sid


def get_client():
    """Get Twilio client instance."""
    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send_verification(to: str, channel: str = "sms") -> bool:
    """
    Send a verification code via Twilio Verify API.
    
    Args:
        to: Phone number (for sms/call) or email address (for email)
        channel: Verification channel - 'sms', 'call', or 'email'
    
    Returns:
        True if verification was sent successfully, False otherwise
    """
    try:
        if TWILIO_ACCOUNT_SID == "placeholder_twilio_sid":
            print(f"DEBUG: Would send {channel.upper()} verification to {to}")
            return True
        
        client = get_client()
        verification = client.verify.v2.services(TWILIO_VERIFY_SERVICE_SID) \
            .verifications \
            .create(to=to, channel=channel)
        
        print(f"Verification sent: {verification.status}")
        return verification.status == "pending"
    except Exception as e:
        print(f"Error sending verification: {e}")
        return False


def check_verification(to: str, code: str) -> bool:
    """
    Check a verification code via Twilio Verify API.
    
    Args:
        to: Phone number or email that received the code
        code: The verification code to check
    
    Returns:
        True if code is valid, False otherwise
    """
    try:
        if TWILIO_ACCOUNT_SID == "placeholder_twilio_sid":
            print(f"DEBUG: Would verify code {code} for {to}")
            # In debug mode, accept any 6-digit code
            return len(code) == 6 and code.isdigit()
        
        client = get_client()
        verification_check = client.verify.v2.services(TWILIO_VERIFY_SERVICE_SID) \
            .verification_checks \
            .create(to=to, code=code)
        
        print(f"Verification check: {verification_check.status}")
        return verification_check.status == "approved"
    except Exception as e:
        print(f"Error checking verification: {e}")
        return False


def send_email_verification(to_email: str) -> bool:
    """
    Send email verification using Twilio Verify.
    
    Args:
        to_email: Email address to send verification to
    
    Returns:
        True if sent successfully
    """
    return send_verification(to_email, channel="email")


def send_sms_verification(to_phone: str) -> bool:
    """
    Send SMS verification using Twilio Verify.
    
    Args:
        to_phone: Phone number to send verification to
    
    Returns:
        True if sent successfully
    """
    return send_verification(to_phone, channel="sms")


def send_call_verification(to_phone: str) -> bool:
    """
    Send voice call verification using Twilio Verify.
    
    Args:
        to_phone: Phone number to call with verification code
    
    Returns:
        True if call initiated successfully
    """
    return send_verification(to_phone, channel="call")
