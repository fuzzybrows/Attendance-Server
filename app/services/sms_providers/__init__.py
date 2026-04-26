"""
SMS provider abstraction and registry.

To add a new provider:
  1. Create a new file in this package (e.g. vonage.py)
  2. Subclass SmsProvider and implement send() and is_configured()
  3. Import and register it in the PROVIDERS dict below
"""
import logging
from abc import ABC, abstractmethod

from app.settings import settings

logger = logging.getLogger(__name__)


class SmsProvider(ABC):
    """Abstract base class for SMS providers."""

    @abstractmethod
    def send(self, to_phone: str, body: str) -> bool:
        """Send an SMS message. Returns True on success, False on failure."""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if this provider has real credentials."""
        ...


class MockSmsProvider(SmsProvider):
    """Logs SMS messages instead of sending. Used when no provider is configured."""

    def send(self, to_phone: str, body: str) -> bool:
        logger.debug(f"Would send SMS to {to_phone}: {body}", extra={"type": "sms_mock", "to_phone": to_phone})
        return True

    def is_configured(self) -> bool:
        return False


# Import concrete providers
from app.services.sms_providers.twilio_messaging import TwilioMessagingProvider  # noqa: E402


# ── Provider Registry ───────────────────────────────────────────────────────
PROVIDERS: dict[str, type[SmsProvider]] = {
    "twilio": TwilioMessagingProvider,
    "mock": MockSmsProvider,
}


def get_sms_provider() -> SmsProvider:
    """Instantiate the SMS provider. Currently always Twilio Messaging."""
    return TwilioMessagingProvider()
