"""
Local OTP service for email and SMS verification.

Uses the app's configured email provider (SendGrid/Mailgun) for email OTPs
and Twilio's Messaging API for SMS OTPs, instead of Twilio Verify.
OTPs are stored in-memory with automatic expiration.
"""
import logging
import time
import threading
from app.services.comm import send_email_otp as _send_otp_email, send_sms_otp as _send_otp_sms, generate_otp
from app.settings import settings

logger = logging.getLogger(__name__)

# Thread-safe in-memory OTP store: { identifier: (code, expiry_timestamp) }
_otp_store: dict[str, tuple[str, float]] = {}
_lock = threading.Lock()
_OTP_EXPIRY = settings.otp_expiry_seconds


def _cleanup_expired():
    """Remove expired entries (called under lock)."""
    now = time.time()
    expired = [k for k, (_, exp) in _otp_store.items() if now > exp]
    for k in expired:
        del _otp_store[k]


def _store_otp(identifier: str) -> str:
    """Generate an OTP and store it for later verification."""
    code = generate_otp()
    with _lock:
        _cleanup_expired()
        _otp_store[identifier] = (code, time.time() + _OTP_EXPIRY)
    return code


def check_local_otp(identifier: str, code: str) -> bool:
    """
    Verify an OTP code against the in-memory store.
    Consumes the OTP on success (one-time use).
    Works for both email and phone identifiers.
    """
    with _lock:
        _cleanup_expired()
        entry = _otp_store.get(identifier)
        if not entry:
            logger.warning(
                f"No OTP found for {identifier}",
                extra={"type": "local_otp_not_found", "identifier": identifier},
            )
            return False

        stored_code, expiry = entry
        if time.time() > expiry:
            del _otp_store[identifier]
            logger.warning(
                f"OTP expired for {identifier}",
                extra={"type": "local_otp_expired", "identifier": identifier},
            )
            return False

        if stored_code != code:
            logger.warning(
                f"OTP mismatch for {identifier}",
                extra={"type": "local_otp_mismatch", "identifier": identifier},
            )
            return False

        # Valid — consume it
        del _otp_store[identifier]
        logger.info(
            f"Local OTP verified for {identifier}",
            extra={"type": "local_otp_verified", "identifier": identifier},
        )
        return True


# ── Channel-specific entry points ──────────────────────────────────────────

def send_local_email_otp(to_email: str) -> bool:
    """Generate an OTP, store it, and send it via the local email provider."""
    code = _store_otp(to_email)
    logger.info(f"Local email OTP generated for {to_email}", extra={"type": "local_otp_email_sent", "to_email": to_email})
    return _send_otp_email(to_email, code)


def check_local_email_otp(to_email: str, code: str) -> bool:
    """Check an email OTP."""
    return check_local_otp(to_email, code)


def send_local_sms_otp(to_phone: str) -> bool:
    """Generate an OTP, store it, and send it via Twilio Messaging API."""
    code = _store_otp(to_phone)
    logger.info(f"Local SMS OTP generated for {to_phone}", extra={"type": "local_otp_sms_sent", "to_phone": to_phone})
    return _send_otp_sms(to_phone, code)


def check_local_sms_otp(to_phone: str, code: str) -> bool:
    """Check an SMS OTP."""
    return check_local_otp(to_phone, code)
