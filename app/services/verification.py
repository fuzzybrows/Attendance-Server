"""
Verification service — single entry point for all OTP verification flows.

Uses the configured verification provider (Twilio or Local Email) via
the same ABC + registry + factory pattern as email_providers.
"""
from app.services.verification_providers import get_verification_provider

# Module-level singleton
_provider = get_verification_provider()


def send_email_verification(to_email: str) -> bool:
    """Send an email verification code."""
    return _provider.send_email(to_email)


def send_sms_verification(to_phone: str) -> bool:
    """Send an SMS verification code."""
    return _provider.send_sms(to_phone)


def check_verification(to: str, code: str) -> bool:
    """Check a verification code (auto-detects email vs phone)."""
    if "@" in to:
        return _provider.check_email(to, code)
    return _provider.check_sms(to, code)
