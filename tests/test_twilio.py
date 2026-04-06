"""
Tests for Twilio service with mocked Twilio client.
Covers the real API call paths (non-placeholder) in services/twilio.py.
"""
from unittest.mock import patch, MagicMock
import importlib
import os
import app.services.twilio as twilio_mod


def _reload_twilio_with_real_sid():
    """
    Reload the twilio module with a non-placeholder SID
    so we exercise the real Twilio Client paths.
    """
    # Temporarily set the module-level constant to a non-placeholder value
    original_sid = twilio_mod.TWILIO_ACCOUNT_SID
    twilio_mod.TWILIO_ACCOUNT_SID = "AC_real_sid_for_testing"
    return twilio_mod, original_sid


def _restore_twilio(twilio_mod, original_sid):
    twilio_mod.TWILIO_ACCOUNT_SID = original_sid


class TestGetClient:
    @patch("app.services.twilio.Client")
    def test_get_client_returns_twilio_client(self, mock_client_cls):
        """Test that get_client creates a Twilio Client with credentials."""
        twilio_mod.get_client()
        mock_client_cls.assert_called_once_with(
            twilio_mod.TWILIO_ACCOUNT_SID,
            twilio_mod.TWILIO_AUTH_TOKEN,
        )


class TestSendVerification:
    def test_send_verification_placeholder_sms(self):
        """Placeholder SID returns True without calling Twilio (debug mode)."""
        result = twilio_mod.send_verification("+15551234567", channel="sms")
        assert result is True

    def test_send_verification_placeholder_email(self):
        """Placeholder mode works for email channel too."""
        result = twilio_mod.send_verification("test@example.com", channel="email")
        assert result is True

    @patch("app.services.twilio.get_client")
    def test_send_verification_real_success(self, mock_get_client):
        """Real Twilio path — verification.status == 'pending' returns True."""
        twilio_mod, original_sid = _reload_twilio_with_real_sid()
        try:
            mock_verification = MagicMock()
            mock_verification.status = "pending"

            mock_service = MagicMock()
            mock_service.verifications.create.return_value = mock_verification
            mock_get_client.return_value.verify.v2.services.return_value = mock_service

            result = twilio_mod.send_verification("+15551234567", channel="sms")
            assert result is True

            mock_service.verifications.create.assert_called_once_with(
                to="+15551234567", channel="sms"
            )
        finally:
            _restore_twilio(twilio_mod, original_sid)

    @patch("app.services.twilio.get_client")
    def test_send_verification_real_failure(self, mock_get_client):
        """Real Twilio path — non-pending status returns False."""
        twilio_mod, original_sid = _reload_twilio_with_real_sid()
        try:
            mock_verification = MagicMock()
            mock_verification.status = "failed"

            mock_service = MagicMock()
            mock_service.verifications.create.return_value = mock_verification
            mock_get_client.return_value.verify.v2.services.return_value = mock_service

            result = twilio_mod.send_verification("+15551234567", channel="sms")
            assert result is False
        finally:
            _restore_twilio(twilio_mod, original_sid)

    @patch("app.services.twilio.get_client")
    def test_send_verification_exception(self, mock_get_client):
        """Real Twilio path — exception returns False."""
        twilio_mod, original_sid = _reload_twilio_with_real_sid()
        try:
            mock_get_client.return_value.verify.v2.services.side_effect = Exception("API error")

            result = twilio_mod.send_verification("+15551234567", channel="sms")
            assert result is False
        finally:
            _restore_twilio(twilio_mod, original_sid)


class TestCheckVerification:
    def test_check_verification_placeholder_valid(self):
        """Placeholder mode accepts 6-digit code."""
        assert twilio_mod.check_verification("+15551234567", "123456") is True

    def test_check_verification_placeholder_invalid(self):
        """Placeholder mode rejects non-6-digit code."""
        assert twilio_mod.check_verification("+15551234567", "abc") is False

    @patch("app.services.twilio.get_client")
    def test_check_verification_real_approved(self, mock_get_client):
        """Real Twilio path — approved status returns True."""
        twilio_mod, original_sid = _reload_twilio_with_real_sid()
        try:
            mock_check = MagicMock()
            mock_check.status = "approved"

            mock_service = MagicMock()
            mock_service.verification_checks.create.return_value = mock_check
            mock_get_client.return_value.verify.v2.services.return_value = mock_service

            result = twilio_mod.check_verification("+15551234567", "123456")
            assert result is True
        finally:
            _restore_twilio(twilio_mod, original_sid)

    @patch("app.services.twilio.get_client")
    def test_check_verification_real_denied(self, mock_get_client):
        """Real Twilio path — non-approved status returns False."""
        twilio_mod, original_sid = _reload_twilio_with_real_sid()
        try:
            mock_check = MagicMock()
            mock_check.status = "denied"

            mock_service = MagicMock()
            mock_service.verification_checks.create.return_value = mock_check
            mock_get_client.return_value.verify.v2.services.return_value = mock_service

            result = twilio_mod.check_verification("+15551234567", "123456")
            assert result is False
        finally:
            _restore_twilio(twilio_mod, original_sid)

    @patch("app.services.twilio.get_client")
    def test_check_verification_exception(self, mock_get_client):
        """Real Twilio path — exception returns False."""
        twilio_mod, original_sid = _reload_twilio_with_real_sid()
        try:
            mock_get_client.return_value.verify.v2.services.side_effect = Exception("API error")

            result = twilio_mod.check_verification("+15551234567", "123456")
            assert result is False
        finally:
            _restore_twilio(twilio_mod, original_sid)


class TestConvenienceFunctions:
    def test_send_email_verification(self):
        """send_email_verification delegates to send_verification with email channel."""
        with patch.object(twilio_mod, "send_verification", return_value=True) as mock:
            result = twilio_mod.send_email_verification("test@example.com")
            assert result is True
            mock.assert_called_once_with("test@example.com", channel="email")

    def test_send_sms_verification(self):
        """send_sms_verification delegates to send_verification with sms channel."""
        with patch.object(twilio_mod, "send_verification", return_value=True) as mock:
            result = twilio_mod.send_sms_verification("+15551234567")
            assert result is True
            mock.assert_called_once_with("+15551234567", channel="sms")

    def test_send_call_verification(self):
        """send_call_verification delegates to send_verification with call channel."""
        with patch.object(twilio_mod, "send_verification", return_value=True) as mock:
            result = twilio_mod.send_call_verification("+15559876543")
            assert result is True
            mock.assert_called_once_with("+15559876543", channel="call")
