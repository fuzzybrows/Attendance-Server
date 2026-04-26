"""Mailgun email provider."""
import logging

import requests as http_requests
from app.settings import settings
from app.services.email_providers import EmailProvider, MockEmailProvider

logger = logging.getLogger(__name__)


class MailgunProvider(EmailProvider):
    """Sends emails via Mailgun REST API."""

    def __init__(self):
        self.api_key = settings.mailgun_api_key
        self.domain = settings.mailgun_domain
        self.from_email = settings.email_from_address

    def is_configured(self) -> bool:
        return self.api_key and self.api_key != "placeholder_mailgun_key" and bool(self.domain)

    def send(self, to_email: str, subject: str, plain_text: str, html: str) -> bool:
        if not self.is_configured():
            return MockEmailProvider().send(to_email, subject, plain_text, html)
        try:
            response = http_requests.post(
                f"https://api.mailgun.net/v3/{self.domain}/messages",
                auth=("api", self.api_key),
                data={
                    "from": self.from_email,
                    "to": to_email,
                    "subject": subject,
                    "text": plain_text,
                    "html": html,
                },
                timeout=10,
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Mailgun error sending to {to_email}: {e}", exc_info=True, extra={"type": "email_mailgun_error", "to_email": to_email, "subject": subject})
            return False
