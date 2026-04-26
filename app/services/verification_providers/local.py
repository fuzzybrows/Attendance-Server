"""Local verification provider — uses the app's own OTP store for all channels."""
import logging

from app.services.verification_providers import VerificationProvider
from app.services.local_otp import (
    send_local_email_otp,
    check_local_email_otp,
    send_local_sms_otp,
    check_local_sms_otp,
)

logger = logging.getLogger(__name__)


class LocalVerificationProvider(VerificationProvider):
    """
    All verification uses the local OTP store.
    Email OTPs are sent via the configured email provider (SendGrid/Mailgun).
    SMS OTPs are sent via Twilio's Messaging API (not Verify).
    """

    def send_email(self, to_email: str) -> bool:
        return send_local_email_otp(to_email)

    def check_email(self, to_email: str, code: str) -> bool:
        return check_local_email_otp(to_email, code)

    def send_sms(self, to_phone: str) -> bool:
        return send_local_sms_otp(to_phone)

    def check_sms(self, to_phone: str, code: str) -> bool:
        return check_local_sms_otp(to_phone, code)
