"""
Tests for scheduler functions: dispatch_24hr_reminders and send_session_reminders.
"""
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.models.session import Session, SessionStatus
from app.models.assignment import Assignment
from app.models.member import Member


def _make_session(id=1, title="Sunday Service", status="scheduled", hours_from_now=24):
    """Create a mock Session with a UTC start_time."""
    session = MagicMock(spec=Session)
    session.id = id
    session.title = title
    session.status = status
    session.start_time = datetime.now(timezone.utc) + timedelta(hours=hours_from_now)
    session.end_time = session.start_time + timedelta(hours=2)
    return session


def _make_member(id=1, first_name="Jane", email="jane@example.com", phone_number="+15551234567", device_token=None):
    """Create a mock Member."""
    member = MagicMock(spec=Member)
    member.id = id
    member.first_name = first_name
    member.email = email
    member.phone_number = phone_number
    member.device_token = device_token
    return member


def _make_assignment(member, role="soprano", session_id=1):
    """Create a mock Assignment linked to a member."""
    assignment = MagicMock(spec=Assignment)
    assignment.member = member
    assignment.role = role
    assignment.session_id = session_id
    return assignment


class TestSendSessionReminders:
    """Tests for the extracted send_session_reminders function."""

    @patch("app.core.scheduler.send_push_notification")
    @patch("app.core.scheduler.send_reminder_sms")
    @patch("app.core.scheduler.send_reminder_email")
    def test_sends_email_and_sms_for_each_assignment(self, mock_email, mock_sms, mock_push):
        from app.core.scheduler import send_session_reminders

        session = _make_session()
        member = _make_member()
        assignment = _make_assignment(member, role="alto")

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [assignment]

        send_session_reminders(session, mock_db)

        mock_email.assert_called_once()
        assert mock_email.call_args.kwargs["to_email"] == "jane@example.com"
        assert mock_email.call_args.kwargs["role"] == "alto"

        mock_sms.assert_called_once()
        assert mock_sms.call_args.kwargs["to_phone"] == "+15551234567"

    @patch("app.core.scheduler.send_push_notification")
    @patch("app.core.scheduler.send_reminder_sms")
    @patch("app.core.scheduler.send_reminder_email")
    def test_skips_sms_when_no_phone_number(self, mock_email, mock_sms, mock_push):
        from app.core.scheduler import send_session_reminders

        session = _make_session()
        member = _make_member(phone_number=None)
        assignment = _make_assignment(member)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [assignment]

        send_session_reminders(session, mock_db)

        mock_email.assert_called_once()
        mock_sms.assert_not_called()

    @patch("app.core.scheduler.send_push_notification")
    @patch("app.core.scheduler.send_reminder_sms")
    @patch("app.core.scheduler.send_reminder_email")
    def test_sends_push_notification_when_device_token_present(self, mock_email, mock_sms, mock_push):
        from app.core.scheduler import send_session_reminders

        session = _make_session()
        member = _make_member(device_token="fcm_token_123")
        assignment = _make_assignment(member, role="lead_singer")

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [assignment]

        send_session_reminders(session, mock_db)

        mock_push.assert_called_once()
        assert mock_push.call_args.kwargs["device_token"] == "fcm_token_123"

    @patch("app.core.scheduler.send_push_notification")
    @patch("app.core.scheduler.send_reminder_sms")
    @patch("app.core.scheduler.send_reminder_email")
    def test_formats_session_time_in_configured_timezone(self, mock_email, mock_sms, mock_push):
        from app.core.scheduler import send_session_reminders, LOCAL_TZ

        # Create a session at a known UTC time: 2026-04-26 00:00 UTC = 2026-04-25 19:00 CDT
        session = _make_session()
        session.start_time = datetime(2026, 4, 26, 0, 0, tzinfo=timezone.utc)

        member = _make_member()
        assignment = _make_assignment(member)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [assignment]

        send_session_reminders(session, mock_db)

        # The session_time passed to send_reminder_email should be in local time, not UTC
        session_time_arg = mock_email.call_args.kwargs["session_time"]
        expected_local = session.start_time.astimezone(LOCAL_TZ)
        expected_str = expected_local.strftime("%A, %B %d at %I:%M %p")
        assert session_time_arg == expected_str

    @patch("app.core.scheduler.send_push_notification")
    @patch("app.core.scheduler.send_reminder_sms")
    @patch("app.core.scheduler.send_reminder_email")
    def test_does_nothing_when_no_assignments_exist(self, mock_email, mock_sms, mock_push):
        from app.core.scheduler import send_session_reminders

        session = _make_session()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        send_session_reminders(session, mock_db)

        mock_email.assert_not_called()
        mock_sms.assert_not_called()
        mock_push.assert_not_called()


class TestDispatch24hrReminders:
    """Tests for the dispatch_24hr_reminders entry point."""

    @patch("app.core.scheduler.send_session_reminders")
    @patch("app.core.scheduler.SessionLocal")
    def test_dispatches_reminders_for_specific_session_id(self, mock_session_local, mock_send):
        from app.core.scheduler import dispatch_24hr_reminders

        mock_session = _make_session(id=42)
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        mock_session_local.return_value = mock_db

        dispatch_24hr_reminders(session_id=42)

        mock_send.assert_called_once_with(mock_session, mock_db)
        mock_db.close.assert_called_once()

    @patch("app.core.scheduler.send_session_reminders")
    @patch("app.core.scheduler.SessionLocal")
    def test_logs_warning_when_session_id_not_found(self, mock_session_local, mock_send):
        from app.core.scheduler import dispatch_24hr_reminders

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_session_local.return_value = mock_db

        dispatch_24hr_reminders(session_id=999)

        mock_send.assert_not_called()
        mock_db.close.assert_called_once()

    @patch("app.core.scheduler.send_session_reminders")
    @patch("app.core.scheduler.SessionLocal")
    def test_queries_upcoming_sessions_when_no_session_id(self, mock_session_local, mock_send):
        from app.core.scheduler import dispatch_24hr_reminders

        session_a = _make_session(id=1, title="Morning Service")
        session_b = _make_session(id=2, title="Evening Service")

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [session_a, session_b]
        mock_session_local.return_value = mock_db

        dispatch_24hr_reminders()

        assert mock_send.call_count == 2
        mock_send.assert_any_call(session_a, mock_db)
        mock_send.assert_any_call(session_b, mock_db)
        mock_db.close.assert_called_once()

    @patch("app.core.scheduler.send_session_reminders")
    @patch("app.core.scheduler.SessionLocal")
    def test_sends_no_reminders_when_no_upcoming_sessions(self, mock_session_local, mock_send):
        from app.core.scheduler import dispatch_24hr_reminders

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_session_local.return_value = mock_db

        dispatch_24hr_reminders()

        mock_send.assert_not_called()
        mock_db.close.assert_called_once()

    @patch("app.core.scheduler.send_session_reminders")
    @patch("app.core.scheduler.SessionLocal")
    def test_closes_db_even_on_exception(self, mock_session_local, mock_send):
        from app.core.scheduler import dispatch_24hr_reminders

        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("DB connection lost")
        mock_session_local.return_value = mock_db

        # Should not raise
        dispatch_24hr_reminders(session_id=1)

        mock_db.close.assert_called_once()
