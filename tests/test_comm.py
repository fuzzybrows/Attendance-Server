"""
Unit tests for app/services/comm.py

All email/SMS provider calls are mocked — no external requests are made.
Tests validate generated HTML, plain text, subjects, and argument structure.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, date, timezone

from app.services.comm import (
    send_email_otp,
    send_sms_otp,
    generate_otp,
    send_reminder_email,
    send_reminder_sms,
    send_leader_summary_email,
    send_push_notification,
    send_availability_reminder_email,
    send_assignment_notification_email,
)


# ─── generate_otp ──────────────────────────────────────────────────────────

class TestGenerateOtp:
    def test_returns_6_digit_string(self):
        otp = generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()

    def test_generates_different_values(self):
        """Generates varied values (not stuck on a single output)."""
        otps = {generate_otp() for _ in range(20)}
        assert len(otps) > 1


# ─── send_email_otp ────────────────────────────────────────────────────────

class TestSendEmailOtp:
    @patch("app.services.comm._send_email", return_value=True)
    def test_returns_true_on_success(self, mock_send):
        result = send_email_otp("user@example.com", "123456")
        assert result is True
        mock_send.assert_called_once()

    @patch("app.services.comm._send_email", return_value=True)
    def test_subject_is_verification_code(self, mock_send):
        send_email_otp("user@example.com", "654321")
        _, subject, _, _ = mock_send.call_args[0]
        assert subject == "Your Verification Code"

    @patch("app.services.comm._send_email", return_value=True)
    def test_otp_appears_in_html_and_plain_text(self, mock_send):
        send_email_otp("user@example.com", "987654")
        _, _, plain_text, html = mock_send.call_args[0]
        assert "987654" in plain_text
        assert "987654" in html

    @patch("app.services.comm._send_email", return_value=True)
    def test_html_is_valid_document(self, mock_send):
        send_email_otp("user@example.com", "111111")
        _, _, _, html = mock_send.call_args[0]
        assert html.strip().startswith("<!DOCTYPE html>")
        assert "</html>" in html


# ─── send_sms_otp ──────────────────────────────────────────────────────────

class TestSendSmsOtp:
    @patch("app.services.comm._send_sms", return_value=True)
    def test_returns_true_on_success(self, mock_send):
        result = send_sms_otp("+15551234567", "123456")
        assert result is True

    @patch("app.services.comm._send_sms", return_value=True)
    def test_body_contains_otp(self, mock_send):
        send_sms_otp("+15551234567", "654321")
        _, body = mock_send.call_args[0]
        assert "654321" in body


# ─── send_reminder_email ───────────────────────────────────────────────────

class TestSendReminderEmail:
    @patch("app.services.comm._send_email", return_value=True)
    def test_returns_true(self, mock_send):
        result = send_reminder_email(
            "alice@example.com", "Alice", "Sunday Service", "lead_singer", "Sun 10:00 AM"
        )
        assert result is True

    @patch("app.services.comm._send_email", return_value=True)
    def test_subject_is_upcoming_session_reminder(self, mock_send):
        send_reminder_email("a@b.com", "Alice", "Sunday Service", "lead_singer", "Sun 10 AM")
        _, subject, _, _ = mock_send.call_args[0]
        assert subject == "Upcoming Session Reminder"

    @patch("app.services.comm._send_email", return_value=True)
    def test_html_contains_member_name_and_role(self, mock_send):
        send_reminder_email("a@b.com", "Alice", "Sunday Service", "lead_singer", "Sun 10 AM")
        _, _, plain_text, html = mock_send.call_args[0]
        assert "Alice" in html
        assert "Lead Singer" in html  # role formatted as title case
        assert "Sunday Service" in html
        assert "Alice" in plain_text
        assert "Lead Singer" in plain_text

    @patch("app.services.comm._send_email", return_value=True)
    def test_html_contains_session_time(self, mock_send):
        send_reminder_email("a@b.com", "Alice", "Rehearsal", "alto", "Wed 7:00 PM")
        _, _, _, html = mock_send.call_args[0]
        assert "Wed 7:00 PM" in html


# ─── send_reminder_sms ─────────────────────────────────────────────────────

class TestSendReminderSms:
    @patch("app.services.comm._send_sms", return_value=True)
    def test_returns_true_on_success(self, mock_send):
        result = send_reminder_sms("+15551234567", "Alice", "Sunday Service", "soprano", "Sun 10 AM")
        assert result is True

    @patch("app.services.comm._send_sms")
    def test_returns_false_when_no_phone(self, mock_send):
        result = send_reminder_sms("", "Alice", "Sunday Service", "soprano", "Sun 10 AM")
        assert result is False
        mock_send.assert_not_called()

    @patch("app.services.comm._send_sms", return_value=True)
    def test_body_contains_session_and_role(self, mock_send):
        send_reminder_sms("+15551234567", "Alice", "Sunday Service", "lead_singer", "Sun 10 AM")
        _, body = mock_send.call_args[0]
        assert "Sunday Service" in body
        assert "Lead Singer" in body
        assert "Alice" in body


# ─── send_leader_summary_email ─────────────────────────────────────────────

class TestSendLeaderSummaryEmail:
    @patch("app.services.comm._send_email", return_value=True)
    def test_returns_true(self, mock_send):
        result = send_leader_summary_email(
            "leader@example.com", "Pastor John",
            "Sunday Service", "Sun 10:00 AM",
            [{"member_name": "Alice", "role": "soprano"}],
            ["Alice", "Bob"],
            ["Charlie"]
        )
        assert result is True

    @patch("app.services.comm._send_email", return_value=True)
    def test_subject_contains_session_title_and_time(self, mock_send):
        send_leader_summary_email(
            "leader@example.com", "Pastor John",
            "Sunday Service", "Sun 10:00 AM",
            [], [], []
        )
        _, subject, _, _ = mock_send.call_args[0]
        assert "Sunday Service" in subject
        assert "Sun 10:00 AM" in subject

    @patch("app.services.comm._send_email", return_value=True)
    def test_html_contains_assignments_and_availability(self, mock_send):
        send_leader_summary_email(
            "leader@example.com", "Pastor John",
            "Sunday Service", "Sun 10:00 AM",
            [{"member_name": "Alice", "role": "soprano"}, {"member_name": "Bob", "role": "lead_singer"}],
            ["Alice", "Bob"],
            ["Charlie"]
        )
        _, _, plain_text, html = mock_send.call_args[0]
        # Assignments
        assert "Alice" in html
        assert "Soprano" in html
        assert "Bob" in html
        assert "Lead Singer" in html
        # Availability
        assert "Charlie" in html
        # Plain text
        assert "Alice" in plain_text
        assert "Charlie" in plain_text

    @patch("app.services.comm._send_email", return_value=True)
    def test_html_shows_no_assignments_message_when_empty(self, mock_send):
        send_leader_summary_email(
            "leader@example.com", "Pastor John",
            "Sunday Service", "Sun 10:00 AM",
            [],  # no assignments
            ["Alice"],
            []
        )
        _, _, _, html = mock_send.call_args[0]
        assert "No assignments yet" in html

    @patch("app.services.comm._send_email", return_value=True)
    def test_html_shows_none_when_no_unavailable(self, mock_send):
        send_leader_summary_email(
            "leader@example.com", "Pastor John",
            "Sunday Service", "Sun 10:00 AM",
            [], ["Alice"], []  # no unavailable
        )
        _, _, _, html = mock_send.call_args[0]
        # The unavailable section should show "None"
        assert "None" in html


# ─── send_push_notification ────────────────────────────────────────────────

class TestSendPushNotification:
    def test_returns_false_for_empty_token(self):
        assert send_push_notification("", "Title", "Body") is False
        assert send_push_notification(None, "Title", "Body") is False

    def test_returns_true_for_valid_token(self):
        """Stub always returns True since Firebase is disabled."""
        assert send_push_notification("device_token_123", "Hello", "World") is True


# ─── send_availability_reminder_email ──────────────────────────────────────

class TestSendAvailabilityReminderEmail:
    @patch("app.services.comm._send_email", return_value=True)
    def test_returns_true(self, mock_send):
        result = send_availability_reminder_email(
            "alice@example.com", "Alice",
            2026, 8,
            set(), {"2026-08-01", "2026-08-08"},
            "https://app.example.com/calendar?month=8&year=2026"
        )
        assert result is True

    @patch("app.services.comm._send_email", return_value=True)
    def test_subject_contains_month_year(self, mock_send):
        send_availability_reminder_email(
            "a@b.com", "Alice", 2026, 8, set(), set(), "https://example.com"
        )
        _, subject, _, _ = mock_send.call_args[0]
        assert "August" in subject
        assert "2026" in subject

    @patch("app.services.comm._send_email", return_value=True)
    def test_html_contains_calendar_grid(self, mock_send):
        send_availability_reminder_email(
            "a@b.com", "Alice", 2026, 8, set(), set(), "https://example.com"
        )
        _, _, _, html = mock_send.call_args[0]
        assert "<table" in html
        assert "Sun" in html  # day headers
        assert "Mon" in html

    @patch("app.services.comm._send_email", return_value=True)
    def test_html_contains_month_year_header(self, mock_send):
        send_availability_reminder_email(
            "a@b.com", "Alice", 2026, 8, set(), set(), "https://example.com"
        )
        _, _, _, html = mock_send.call_args[0]
        assert "August 2026" in html

    @patch("app.services.comm._send_email", return_value=True)
    def test_html_contains_member_name(self, mock_send):
        send_availability_reminder_email(
            "a@b.com", "Alice", 2026, 8, set(), set(), "https://example.com"
        )
        _, _, plain_text, html = mock_send.call_args[0]
        assert "Alice" in html
        assert "Alice" in plain_text

    @patch("app.services.comm._send_email", return_value=True)
    def test_html_contains_cta_link(self, mock_send):
        url = "https://example.com/calendar?month=8&year=2026"
        send_availability_reminder_email("a@b.com", "Alice", 2026, 8, set(), set(), url)
        _, _, _, html = mock_send.call_args[0]
        assert url in html

    @patch("app.services.comm._send_email", return_value=True)
    def test_unavailable_days_shown_in_summary(self, mock_send):
        send_availability_reminder_email(
            "a@b.com", "Alice", 2026, 8,
            {"2026-08-10", "2026-08-17"},  # 2 unavailable dates
            set(),
            "https://example.com"
        )
        _, _, plain_text, html = mock_send.call_args[0]
        assert "2" in html  # count of unavailable days
        assert "unavailable" in plain_text.lower()

    @patch("app.services.comm._send_email", return_value=True)
    def test_has_background_color_fallback_for_gradients(self, mock_send):
        """Ensure linear-gradient has a background-color fallback for Yahoo Mail."""
        send_availability_reminder_email(
            "a@b.com", "Alice", 2026, 8, set(), set(), "https://example.com"
        )
        _, _, _, html = mock_send.call_args[0]
        assert "background-color:" in html
        assert "linear-gradient" in html


# ─── send_assignment_notification_email ────────────────────────────────────

class TestSendAssignmentNotificationEmail:
    @patch("app.services.comm._send_email", return_value=True)
    def test_with_assignments_returns_true(self, mock_send):
        result = send_assignment_notification_email(
            "alice@example.com", "Alice", 2026, 12,
            [{"session_title": "Sunday Service", "role": "soprano",
              "start_time": datetime(2026, 12, 6, 10, 0, 0, tzinfo=timezone.utc),
              "end_time": datetime(2026, 12, 6, 13, 0, 0, tzinfo=timezone.utc)}],
            "https://example.com/calendar",
            b"BEGIN:VCALENDAR\r\nEND:VCALENDAR",
        )
        assert result is True

    @patch("app.services.comm._send_email", return_value=True)
    def test_without_assignments_returns_true(self, mock_send):
        result = send_assignment_notification_email(
            "alice@example.com", "Alice", 2026, 12, [],
            "https://example.com/calendar",
        )
        assert result is True

    @patch("app.services.comm._send_email", return_value=True)
    def test_subject_says_assignments_ready_when_assigned(self, mock_send):
        send_assignment_notification_email(
            "a@b.com", "Alice", 2026, 12,
            [{"session_title": "S", "role": "soprano",
              "start_time": datetime(2026, 12, 6, 10, 0, tzinfo=timezone.utc), "end_time": datetime(2026, 12, 6, 13, 0, tzinfo=timezone.utc)}],
            "https://example.com",
        )
        _, subject, _, _, _ = mock_send.call_args[0]
        assert "Assignments Are Ready" in subject

    @patch("app.services.comm._send_email", return_value=True)
    def test_subject_says_schedule_published_when_no_assignments(self, mock_send):
        send_assignment_notification_email(
            "a@b.com", "Alice", 2026, 12, [], "https://example.com",
        )
        _, subject, _, _, _ = mock_send.call_args[0]
        assert "Schedule Published" in subject

    @patch("app.services.comm._send_email", return_value=True)
    def test_html_contains_calendar_grid_and_month_header(self, mock_send):
        send_assignment_notification_email(
            "a@b.com", "Alice", 2026, 12,
            [{"session_title": "Service", "role": "soprano",
              "start_time": datetime(2026, 12, 6, 10, 0, tzinfo=timezone.utc), "end_time": datetime(2026, 12, 6, 13, 0, tzinfo=timezone.utc)}],
            "https://example.com",
        )
        _, _, _, html, _ = mock_send.call_args[0]
        assert "<table" in html
        assert "December 2026" in html
        assert "Sun" in html

    @patch("app.services.comm._send_email", return_value=True)
    def test_html_contains_assignment_table_with_role(self, mock_send):
        send_assignment_notification_email(
            "a@b.com", "Alice", 2026, 12,
            [{"session_title": "Sunday Service", "role": "lead_singer",
              "start_time": datetime(2026, 12, 6, 10, 0, tzinfo=timezone.utc), "end_time": datetime(2026, 12, 6, 13, 0, tzinfo=timezone.utc)}],
            "https://example.com",
        )
        _, _, _, html, _ = mock_send.call_args[0]
        assert "Lead Singer" in html
        assert "Sunday Service" in html

    @patch("app.services.comm._send_email", return_value=True)
    def test_html_contains_google_calendar_link(self, mock_send):
        send_assignment_notification_email(
            "a@b.com", "Alice", 2026, 12,
            [{"session_title": "Service", "role": "soprano",
              "start_time": datetime(2026, 12, 6, 10, 0, tzinfo=timezone.utc), "end_time": datetime(2026, 12, 6, 13, 0, tzinfo=timezone.utc)}],
            "https://example.com",
        )
        _, _, _, html, _ = mock_send.call_args[0]
        assert "calendar.google.com/calendar/r/eventedit" in html
        assert "&amp;dates=" in html  # HTML-escaped & for valid href

    @patch("app.services.comm._send_email", return_value=True)
    def test_html_contains_ics_explanation(self, mock_send):
        send_assignment_notification_email(
            "a@b.com", "Alice", 2026, 12,
            [{"session_title": "S", "role": "soprano",
              "start_time": datetime(2026, 12, 6, 10, 0, tzinfo=timezone.utc), "end_time": datetime(2026, 12, 6, 13, 0, tzinfo=timezone.utc)}],
            "https://example.com",
        )
        _, _, _, html, _ = mock_send.call_args[0]
        assert "Adding to Your Calendar" in html
        assert ".ics file" in html
        assert "Google Cal" in html

    @patch("app.services.comm._send_email", return_value=True)
    def test_ics_attachment_passed_when_provided(self, mock_send):
        ics = b"BEGIN:VCALENDAR\r\nEND:VCALENDAR"
        send_assignment_notification_email(
            "a@b.com", "Alice", 2026, 12,
            [{"session_title": "S", "role": "soprano",
              "start_time": datetime(2026, 12, 6, 10, 0, tzinfo=timezone.utc), "end_time": datetime(2026, 12, 6, 13, 0, tzinfo=timezone.utc)}],
            "https://example.com",
            ics_bytes=ics,
        )
        attachments = mock_send.call_args[0][4]
        assert attachments is not None
        assert len(attachments) == 1
        assert attachments[0]["filename"].endswith(".ics")
        assert attachments[0]["mime_type"] == "text/calendar"
        assert attachments[0]["content"] == ics

    @patch("app.services.comm._send_email", return_value=True)
    def test_no_attachment_when_no_assignments(self, mock_send):
        send_assignment_notification_email(
            "a@b.com", "Alice", 2026, 12, [], "https://example.com",
            ics_bytes=b"dummy",
        )
        attachments = mock_send.call_args[0][4]
        assert attachments is None

    @patch("app.services.comm._send_email", return_value=True)
    def test_no_assignments_shows_info_message(self, mock_send):
        send_assignment_notification_email(
            "a@b.com", "Alice", 2026, 12, [], "https://example.com",
        )
        _, _, plain_text, html, _ = mock_send.call_args[0]
        assert "no assignments" in html.lower()
        assert "no assignments" in plain_text.lower()

    @patch("app.services.comm._send_email", return_value=True)
    def test_html_has_background_color_fallback(self, mock_send):
        """Ensure linear-gradient has a background-color fallback for Yahoo Mail."""
        send_assignment_notification_email(
            "a@b.com", "Alice", 2026, 12,
            [{"session_title": "S", "role": "soprano",
              "start_time": datetime(2026, 12, 6, 10, 0, tzinfo=timezone.utc), "end_time": datetime(2026, 12, 6, 13, 0, tzinfo=timezone.utc)}],
            "https://example.com",
        )
        _, _, _, html, _ = mock_send.call_args[0]
        assert "background-color:" in html
        assert "linear-gradient" in html

    @patch("app.services.comm._send_email", return_value=True)
    def test_plain_text_lists_assignments(self, mock_send):
        send_assignment_notification_email(
            "a@b.com", "Alice", 2026, 12,
            [{"session_title": "Sunday Service", "role": "lead_singer",
              "start_time": datetime(2026, 12, 6, 10, 0, tzinfo=timezone.utc), "end_time": datetime(2026, 12, 6, 13, 0, tzinfo=timezone.utc)}],
            "https://example.com",
        )
        _, _, plain_text, _, _ = mock_send.call_args[0]
        assert "Sunday Service" in plain_text
        assert "Lead Singer" in plain_text
