"""Twilio Verify provider — uses Twilio for both email and SMS verification."""
import logging

from app.services.verification_providers import VerificationProvider
from app.services.twilio import send_verification, check_verification

logger = logging.getLogger(__name__)


class TwilioVerificationProvider(VerificationProvider):
    """All verification channels go through Twilio Verify."""

    def send_email(self, to_email: str) -> bool:
        return send_verification(to_email, channel="email")

    def check_email(self, to_email: str, code: str) -> bool:
        return check_verification(to_email, code)

    def send_sms(self, to_phone: str) -> bool:
        return send_verification(to_phone, channel="sms")

    def check_sms(self, to_phone: str, code: str) -> bool:
        return check_verification(to_phone, code)
