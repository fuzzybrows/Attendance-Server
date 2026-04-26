"""
Twilio Verify API service for OTP verification.
Uses Twilio's managed Verify service for SMS, call, and email channels.
"""
import logging

from twilio.rest import Client
from app.settings import settings

logger = logging.getLogger(__name__)

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
            logger.debug(f"Would send {channel.upper()} verification to {to}", extra={"type": "twilio_verify_mock", "channel": channel, "to": to})
            return True
        
        client = get_client()
        verification = client.verify.v2.services(TWILIO_VERIFY_SERVICE_SID) \
            .verifications \
            .create(to=to, channel=channel)
        
        logger.info(f"Verification sent: {verification.status}", extra={"type": "twilio_verify_sent", "channel": channel, "to": to, "status": verification.status})
        return verification.status == "pending"
    except Exception as e:
        logger.error(f"Error sending verification: {e}", exc_info=True, extra={"type": "twilio_verify_error", "channel": channel, "to": to})
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
            logger.debug(f"Would verify code {code} for {to}", extra={"type": "twilio_check_mock", "to": to})
            # In debug mode, accept any 6-digit code
            return len(code) == 6 and code.isdigit()
        
        client = get_client()
        verification_check = client.verify.v2.services(TWILIO_VERIFY_SERVICE_SID) \
            .verification_checks \
            .create(to=to, code=code)
        
        logger.info(f"Verification check: {verification_check.status}", extra={"type": "twilio_check_result", "to": to, "status": verification_check.status})
        return verification_check.status == "approved"
    except Exception as e:
        logger.error(f"Error checking verification: {e}", exc_info=True, extra={"type": "twilio_check_error", "to": to})
        return False

