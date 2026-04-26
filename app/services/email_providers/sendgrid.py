"""SendGrid email provider."""
import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.settings import settings
from app.services.email_providers import EmailProvider, MockEmailProvider

logger = logging.getLogger(__name__)


class SendGridProvider(EmailProvider):
    """Sends emails via SendGrid."""

    def __init__(self):
        self.api_key = settings.sendgrid_api_key
        self.from_email = settings.email_from_address

    def is_configured(self) -> bool:
        return self.api_key and self.api_key != "placeholder_sendgrid_key"

    def send(self, to_email: str, subject: str, plain_text: str, html: str) -> bool:
        if not self.is_configured():
            return MockEmailProvider().send(to_email, subject, plain_text, html)
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                plain_text_content=plain_text,
                html_content=html,
            )
            sg = SendGridAPIClient(self.api_key)
            sg.send(message)
            return True
        except Exception as e:
            logger.error(f"SendGrid error sending to {to_email}: {e}", exc_info=True, extra={"type": "email_sendgrid_error", "to_email": to_email, "subject": subject})
            return False
