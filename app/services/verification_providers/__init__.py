"""
Verification provider abstraction and registry.

To add a new provider:
  1. Create a new file in this package (e.g. amazon_sns.py)
  2. Subclass VerificationProvider and implement send_email / check_email
  3. Import and register it in the PROVIDERS dict below
"""
import logging
from abc import ABC, abstractmethod

from app.settings import settings, VerificationProviderType

logger = logging.getLogger(__name__)


class VerificationProvider(ABC):
    """Abstract base class for verification providers."""

    @abstractmethod
    def send_email(self, to_email: str) -> bool:
        """Send a verification code to an email address."""
        ...

    @abstractmethod
    def check_email(self, to_email: str, code: str) -> bool:
        """Verify a code sent to an email address."""
        ...

    @abstractmethod
    def send_sms(self, to_phone: str) -> bool:
        """Send a verification code via SMS."""
        ...

    @abstractmethod
    def check_sms(self, to_phone: str, code: str) -> bool:
        """Verify a code sent via SMS."""
        ...


# Import concrete providers
from app.services.verification_providers.twilio_verify import TwilioVerificationProvider  # noqa: E402
from app.services.verification_providers.local import LocalVerificationProvider  # noqa: E402


# ── Provider Registry ───────────────────────────────────────────────────────
# Add new providers here: VerificationProviderType.X -> ProviderClass
PROVIDERS: dict[VerificationProviderType, type[VerificationProvider]] = {
    VerificationProviderType.TWILIO_VERIFY: TwilioVerificationProvider,
    VerificationProviderType.LOCAL: LocalVerificationProvider,
}


def get_verification_provider() -> VerificationProvider:
    """Instantiate the configured verification provider."""
    provider_name = settings.verification_provider
    provider_cls = PROVIDERS.get(provider_name)
    if not provider_cls:
        logger.warning(
            f"Unknown verification provider '{provider_name}', falling back to Twilio",
            extra={"type": "verification_provider_fallback", "provider": provider_name},
        )
        return TwilioVerificationProvider()
    return provider_cls()
