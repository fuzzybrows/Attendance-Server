"""
Tests for the local OTP service (app/services/local_otp.py).
Covers OTP generation, storage, expiry, one-time use, and both email/SMS channels.
"""
import time
from unittest.mock import patch

from app.services.local_otp import (
    _otp_store,
    _lock,
    send_local_email_otp,
    check_local_email_otp,
    send_local_sms_otp,
    check_local_sms_otp,
    check_local_otp,
)


def _clear_store():
    """Helper to reset the OTP store between tests."""
    with _lock:
        _otp_store.clear()


class TestLocalEmailOtp:
    """Tests for the email OTP channel."""

    @patch("app.services.local_otp._send_otp_email", return_value=True)
    def test_send_stores_otp_and_sends_email(self, mock_send):
        _clear_store()
        result = send_local_email_otp("jane@example.com")

        assert result is True
        mock_send.assert_called_once()
        assert mock_send.call_args[0][0] == "jane@example.com"
        # OTP should be a 6-digit string
        otp = mock_send.call_args[0][1]
        assert len(otp) == 6 and otp.isdigit()

    @patch("app.services.local_otp._send_otp_email", return_value=True)
    def test_check_correct_code_returns_true(self, mock_send):
        _clear_store()
        send_local_email_otp("jane@example.com")
        otp = mock_send.call_args[0][1]

        assert check_local_email_otp("jane@example.com", otp) is True

    @patch("app.services.local_otp._send_otp_email", return_value=True)
    def test_check_wrong_code_returns_false(self, mock_send):
        _clear_store()
        send_local_email_otp("jane@example.com")

        assert check_local_email_otp("jane@example.com", "000000") is False

    @patch("app.services.local_otp._send_otp_email", return_value=True)
    def test_otp_is_consumed_after_successful_check(self, mock_send):
        _clear_store()
        send_local_email_otp("jane@example.com")
        otp = mock_send.call_args[0][1]

        assert check_local_email_otp("jane@example.com", otp) is True
        # Second check should fail — OTP was consumed
        assert check_local_email_otp("jane@example.com", otp) is False

    def test_check_nonexistent_identifier_returns_false(self):
        _clear_store()
        assert check_local_email_otp("nobody@example.com", "123456") is False

    @patch("app.services.local_otp._send_otp_email", return_value=True)
    @patch("app.services.local_otp.time")
    def test_expired_otp_returns_false(self, mock_time, mock_send):
        _clear_store()
        # Send at t=1000
        mock_time.time.return_value = 1000.0
        send_local_email_otp("jane@example.com")
        otp = mock_send.call_args[0][1]

        # Check at t=1400 (past 300s expiry)
        mock_time.time.return_value = 1400.0
        assert check_local_email_otp("jane@example.com", otp) is False


class TestLocalSmsOtp:
    """Tests for the SMS OTP channel."""

    @patch("app.services.local_otp._send_otp_sms", return_value=True)
    def test_send_stores_otp_and_sends_sms(self, mock_send):
        _clear_store()
        result = send_local_sms_otp("+15551234567")

        assert result is True
        mock_send.assert_called_once()
        assert mock_send.call_args[0][0] == "+15551234567"
        otp = mock_send.call_args[0][1]
        assert len(otp) == 6 and otp.isdigit()

    @patch("app.services.local_otp._send_otp_sms", return_value=True)
    def test_check_correct_code_returns_true(self, mock_send):
        _clear_store()
        send_local_sms_otp("+15551234567")
        otp = mock_send.call_args[0][1]

        assert check_local_sms_otp("+15551234567", otp) is True

    @patch("app.services.local_otp._send_otp_sms", return_value=True)
    def test_check_wrong_code_returns_false(self, mock_send):
        _clear_store()
        send_local_sms_otp("+15551234567")

        assert check_local_sms_otp("+15551234567", "000000") is False

    @patch("app.services.local_otp._send_otp_sms", return_value=True)
    def test_sms_otp_is_consumed_after_successful_check(self, mock_send):
        _clear_store()
        send_local_sms_otp("+15551234567")
        otp = mock_send.call_args[0][1]

        assert check_local_sms_otp("+15551234567", otp) is True
        assert check_local_sms_otp("+15551234567", otp) is False


class TestLocalOtpSharedStore:
    """Tests verifying that email and SMS share the same OTP store."""

    @patch("app.services.local_otp._send_otp_email", return_value=True)
    @patch("app.services.local_otp._send_otp_sms", return_value=True)
    def test_email_and_sms_otps_are_independent(self, mock_sms, mock_email):
        _clear_store()
        send_local_email_otp("jane@example.com")
        send_local_sms_otp("+15551234567")

        email_otp = mock_email.call_args[0][1]
        sms_otp = mock_sms.call_args[0][1]

        # Each identifier resolves its own OTP
        assert check_local_otp("jane@example.com", email_otp) is True
        assert check_local_otp("+15551234567", sms_otp) is True

    @patch("app.services.local_otp._send_otp_email", return_value=True)
    def test_resend_overwrites_previous_otp(self, mock_send):
        _clear_store()
        send_local_email_otp("jane@example.com")
        first_otp = mock_send.call_args[0][1]

        send_local_email_otp("jane@example.com")
        second_otp = mock_send.call_args[0][1]

        # Only the latest OTP should work
        if first_otp != second_otp:
            assert check_local_email_otp("jane@example.com", first_otp) is False
        assert check_local_email_otp("jane@example.com", second_otp) is True

    @patch("app.services.local_otp._send_otp_email", return_value=False)
    def test_send_returns_false_when_delivery_fails(self, mock_send):
        _clear_store()
        result = send_local_email_otp("jane@example.com")
        assert result is False
        # OTP is still stored even if delivery fails (user can retry)
        assert "jane@example.com" in _otp_store
