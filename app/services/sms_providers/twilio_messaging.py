"""Twilio Messaging SMS provider."""
import logging

from twilio.rest import Client
from app.settings import settings
from app.services.sms_providers import SmsProvider, MockSmsProvider

logger = logging.getLogger(__name__)


class TwilioMessagingProvider(SmsProvider):
    """Sends SMS via Twilio's Messaging API."""

    def __init__(self):
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.from_number = settings.twilio_phone_number

    def is_configured(self) -> bool:
        return self.account_sid and self.account_sid != "placeholder_twilio_sid"

    def send(self, to_phone: str, body: str) -> bool:
        if not self.is_configured():
            return MockSmsProvider().send(to_phone, body)
        try:
            client = Client(self.account_sid, self.auth_token)
            client.messages.create(
                body=body,
                from_=self.from_number,
                to=to_phone,
            )
            return True
        except Exception as e:
            logger.error(f"Twilio SMS error sending to {to_phone}: {e}", exc_info=True, extra={"type": "sms_twilio_error", "to_phone": to_phone})
            return False
