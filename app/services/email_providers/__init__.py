"""
Email provider abstraction and registry.

To add a new provider:
  1. Create a new file in this package (e.g. ses.py)
  2. Subclass EmailProvider and implement send() and is_configured()
  3. Import and register it in the PROVIDERS dict below
"""
import logging
from abc import ABC, abstractmethod

from app.settings import settings, EmailProviderType

logger = logging.getLogger(__name__)


class EmailProvider(ABC):
    """Abstract base class for email providers."""

    @abstractmethod
    def send(self, to_email: str, subject: str, plain_text: str, html: str, attachments: list = None) -> bool:
        """Send an email. Returns True on success, False on failure.

        Args:
            attachments: Optional list of dicts with keys:
                - filename (str): e.g. 'schedule.ics'
                - content (bytes): file content
                - mime_type (str): e.g. 'text/calendar'
        """
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if this provider has real credentials (not placeholders)."""
        ...


class MockEmailProvider(EmailProvider):
    """Logs emails instead of sending. Used when no provider is configured."""

    def send(self, to_email: str, subject: str, plain_text: str, html: str, attachments: list = None) -> bool:
        attachment_info = f" with {len(attachments)} attachment(s)" if attachments else ""
        logger.debug(f"Would send email to {to_email}: {subject}{attachment_info}", extra={"type": "email_mock", "to_email": to_email, "subject": subject})
        return True

    def is_configured(self) -> bool:
        return False


# Import concrete providers
from app.services.email_providers.sendgrid import SendGridProvider  # noqa: E402
from app.services.email_providers.mailgun import MailgunProvider  # noqa: E402


# ── Provider Registry ───────────────────────────────────────────────────────
# Add new providers here: EmailProviderType.X -> ProviderClass
PROVIDERS: dict[EmailProviderType, type[EmailProvider]] = {
    EmailProviderType.SENDGRID: SendGridProvider,
    EmailProviderType.MAILGUN: MailgunProvider,
    EmailProviderType.MOCK: MockEmailProvider,
}


def get_email_provider() -> EmailProvider:
    """Instantiate the configured email provider."""
    provider_name = settings.email_provider
    provider_cls = PROVIDERS.get(provider_name)
    if not provider_cls:
        logger.warning(
            f"Unknown email provider '{provider_name}', falling back to mock",
            extra={"type": "email_provider_fallback", "provider": provider_name},
        )
        return MockEmailProvider()
    return provider_cls()
