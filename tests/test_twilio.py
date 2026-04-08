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
    def test_get_client_successfully_instantiates_twilio_client_with_configured_credentials(self, mock_client_cls):
        twilio_mod.get_client()
        mock_client_cls.assert_called_once_with(
            twilio_mod.TWILIO_ACCOUNT_SID,
            twilio_mod.TWILIO_AUTH_TOKEN,
        )


class TestSendVerification:
    def test_send_verification_returns_true_in_placeholder_sms_mode_without_calling_twilio(self):
        result = twilio_mod.send_verification("+15551234567", channel="sms")
        assert result is True

    def test_send_verification_returns_true_in_placeholder_email_mode_without_calling_twilio(self):
        result = twilio_mod.send_verification("test@example.com", channel="email")
        assert result is True

    @patch("app.services.twilio.get_client")
    def test_send_verification_returns_true_when_real_twilio_status_is_pending(self, mock_get_client):
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
    def test_send_verification_returns_false_when_real_twilio_status_is_not_pending(self, mock_get_client):
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
    def test_send_verification_returns_false_when_real_twilio_api_raises_exception(self, mock_get_client):
        twilio_mod, original_sid = _reload_twilio_with_real_sid()
        try:
            mock_get_client.return_value.verify.v2.services.side_effect = Exception("API error")

            result = twilio_mod.send_verification("+15551234567", channel="sms")
            assert result is False
        finally:
            _restore_twilio(twilio_mod, original_sid)


class TestCheckVerification:
    def test_check_verification_returns_true_for_six_digit_code_in_placeholder_mode(self):
        assert twilio_mod.check_verification("+15551234567", "123456") is True

    def test_check_verification_returns_false_for_non_six_digit_code_in_placeholder_mode(self):
        assert twilio_mod.check_verification("+15551234567", "abc") is False

    @patch("app.services.twilio.get_client")
    def test_check_verification_returns_true_when_real_twilio_status_is_approved(self, mock_get_client):
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
    def test_check_verification_returns_false_when_real_twilio_status_is_denied(self, mock_get_client):
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
    def test_check_verification_returns_false_when_real_twilio_api_raises_exception(self, mock_get_client):
        twilio_mod, original_sid = _reload_twilio_with_real_sid()
        try:
            mock_get_client.return_value.verify.v2.services.side_effect = Exception("API error")

            result = twilio_mod.check_verification("+15551234567", "123456")
            assert result is False
        finally:
            _restore_twilio(twilio_mod, original_sid)


class TestConvenienceFunctions:
    def test_send_email_verification_successfully_delegates_to_base_send_function_with_email_channel(self):
        with patch.object(twilio_mod, "send_verification", return_value=True) as mock:
            result = twilio_mod.send_email_verification("test@example.com")
            assert result is True
            mock.assert_called_once_with("test@example.com", channel="email")

    def test_send_sms_verification_successfully_delegates_to_base_send_function_with_sms_channel(self):
        with patch.object(twilio_mod, "send_verification", return_value=True) as mock:
            result = twilio_mod.send_sms_verification("+15551234567")
            assert result is True
            mock.assert_called_once_with("+15551234567", channel="sms")

    def test_send_call_verification_successfully_delegates_to_base_send_function_with_call_channel(self):
        with patch.object(twilio_mod, "send_verification", return_value=True) as mock:
            result = twilio_mod.send_call_verification("+15559876543")
            assert result is True
            mock.assert_called_once_with("+15559876543", channel="call")
