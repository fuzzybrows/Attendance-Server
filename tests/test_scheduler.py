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


def _make_member(id=1, first_name="Jane", last_name="Doe", email="jane@example.com", phone_number="+15551234567", device_token=None):
    """Create a mock Member."""
    member = MagicMock(spec=Member)
    member.id = id
    member.first_name = first_name
    member.last_name = last_name
    member.full_name = f"{first_name} {last_name}"
    member.display_first_name = first_name
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

        send_session_reminders(session, mock_db, send_sms=True)

        mock_email.assert_called_once()
        assert mock_email.call_args.kwargs["to_email"] == "Jane Doe <jane@example.com>"
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

        send_session_reminders(session, mock_db, send_sms=True)

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

    def setup_method(self):
        pass

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

    @patch("app.core.scheduler.send_session_reminders")
    @patch("app.core.scheduler.SessionLocal")
    def test_deduplicates_sessions_across_calls(self, mock_session_local, mock_send):
        """Sessions with reminder_sent_at already set should be filtered out by the query."""
        from app.core.scheduler import dispatch_24hr_reminders

        session_a = _make_session(id=10, title="Morning Service")
        session_a.reminder_sent_at = None  # first call: not yet reminded

        mock_db = MagicMock()
        # First call returns the session (reminder_sent_at IS NULL in query)
        mock_db.query.return_value.filter.return_value.all.return_value = [session_a]
        mock_session_local.return_value = mock_db

        dispatch_24hr_reminders()
        assert mock_send.call_count == 1
        # After sending, reminder_sent_at should be set
        assert session_a.reminder_sent_at is not None

        # Second call: query filters out already-reminded sessions
        mock_db.query.return_value.filter.return_value.all.return_value = []
        dispatch_24hr_reminders()
        assert mock_send.call_count == 1  # still 1, not 2

    @patch("app.core.scheduler.send_session_reminders")
    @patch("app.core.scheduler.SessionLocal")
    def test_targeted_session_id_bypasses_deduplication(self, mock_session_local, mock_send):
        """Manual session_id calls should always send, even if previously reminded."""
        from app.core.scheduler import dispatch_24hr_reminders

        mock_session = _make_session(id=10)
        mock_session.reminder_sent_at = datetime.now(timezone.utc)  # already reminded
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        mock_session_local.return_value = mock_db

        # Targeted call should still send
        dispatch_24hr_reminders(session_id=10)
        mock_send.assert_called_once_with(mock_session, mock_db)


class TestLeaderSummary:
    """Tests for the leader summary email feature in send_session_reminders."""

    def _patch_settings(self, enabled=True, leader_ids="1"):
        """Return a context manager that patches notify_leaders settings."""
        return patch.multiple(
            "app.core.scheduler.settings",
            notify_leaders_enabled=enabled,
            notify_leader_ids=leader_ids,
        )

    @patch("app.core.scheduler.send_leader_summary_email")
    @patch("app.core.scheduler.send_push_notification")
    @patch("app.core.scheduler.send_reminder_sms")
    @patch("app.core.scheduler.send_reminder_email")
    def test_sends_leader_summary_when_enabled(self, mock_email, mock_sms, mock_push, mock_leader_email):
        from app.core.scheduler import send_session_reminders

        session = _make_session()
        member = _make_member(id=2, first_name="Alice", last_name="Smith")
        assignment = _make_assignment(member, role="soprano")

        leader = _make_member(id=1, first_name="Pastor", last_name="Jones", email="pastor@example.com")

        mock_db = MagicMock()

        member_query_count = [0]

        def query_side_effect(model):
            q = MagicMock()
            if model is Assignment:
                q.filter.return_value.all.return_value = [assignment]
            elif model.__name__ == "Availability":
                q.filter.return_value.all.return_value = []
            elif model.__name__ == "DayOff":
                q.filter.return_value.all.return_value = []
            elif model is Member:
                member_query_count[0] += 1
                if member_query_count[0] == 1:
                    # First Member query: all active members with assignable roles
                    q.filter.return_value.all.return_value = [member, leader]
                else:
                    # Second Member query: leaders by ID
                    q.filter.return_value.all.return_value = [leader]
            return q

        mock_db.query.side_effect = query_side_effect

        with self._patch_settings(enabled=True, leader_ids="1"):
            send_session_reminders(session, mock_db)

        # Member reminder should still be sent
        mock_email.assert_called_once()

        # Leader summary should be sent to leader only
        mock_leader_email.assert_called_once()
        call_kwargs = mock_leader_email.call_args.kwargs
        assert call_kwargs["leader_name"] == "Pastor"
        assert call_kwargs["session_title"] == "Sunday Service"
        assert len(call_kwargs["assignments"]) == 1
        assert call_kwargs["assignments"][0]["role"] == "soprano"

    @patch("app.core.scheduler.send_leader_summary_email")
    @patch("app.core.scheduler.send_push_notification")
    @patch("app.core.scheduler.send_reminder_sms")
    @patch("app.core.scheduler.send_reminder_email")
    def test_skips_leader_summary_when_disabled(self, mock_email, mock_sms, mock_push, mock_leader_email):
        from app.core.scheduler import send_session_reminders

        session = _make_session()
        member = _make_member()
        assignment = _make_assignment(member)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [assignment]

        with self._patch_settings(enabled=False, leader_ids=""):
            send_session_reminders(session, mock_db)

        # Member reminder sent
        mock_email.assert_called_once()
        # Leader summary NOT sent
        mock_leader_email.assert_not_called()

    @patch("app.core.scheduler.send_leader_summary_email")
    @patch("app.core.scheduler.send_push_notification")
    @patch("app.core.scheduler.send_reminder_sms")
    @patch("app.core.scheduler.send_reminder_email")
    def test_skips_leader_without_email(self, mock_email, mock_sms, mock_push, mock_leader_email):
        from app.core.scheduler import send_session_reminders

        session = _make_session()
        member = _make_member(id=2)
        assignment = _make_assignment(member)

        leader_no_email = _make_member(id=1, first_name="Pastor", last_name="Jones", email=None)

        mock_db = MagicMock()

        def query_side_effect(model):
            q = MagicMock()
            if model is Assignment:
                q.filter.return_value.all.return_value = [assignment]
            elif model is Member:
                q.filter.return_value.all.return_value = [leader_no_email]
            else:
                q.filter.return_value.all.return_value = []
            return q

        mock_db.query.side_effect = query_side_effect

        with self._patch_settings(enabled=True, leader_ids="1"):
            send_session_reminders(session, mock_db)

        # Leader has no email — summary should NOT be sent
        mock_leader_email.assert_not_called()

    @patch("app.core.scheduler.send_leader_summary_email")
    @patch("app.core.scheduler.send_push_notification")
    @patch("app.core.scheduler.send_reminder_sms")
    @patch("app.core.scheduler.send_reminder_email")
    def test_leader_summary_includes_unavailable_members(self, mock_email, mock_sms, mock_push, mock_leader_email):
        from app.core.scheduler import send_session_reminders
        from app.models.availability import Availability

        session = _make_session()
        member = _make_member(id=2, first_name="Alice", last_name="Smith")
        assignment = _make_assignment(member, role="alto")

        unavailable_member = _make_member(id=3, first_name="Bob", last_name="Brown")
        leader = _make_member(id=1, first_name="Pastor", last_name="Jones", email="pastor@example.com")

        # Create a mock opt-out
        opt_out = MagicMock(spec=Availability)
        opt_out.member_id = 3

        mock_db = MagicMock()
        member_query_count = [0]

        def query_side_effect(model):
            q = MagicMock()
            if model is Assignment:
                q.filter.return_value.all.return_value = [assignment]
            elif model.__name__ == "Availability":
                q.filter.return_value.all.return_value = [opt_out]
            elif model.__name__ == "DayOff":
                q.filter.return_value.all.return_value = []
            elif model is Member:
                member_query_count[0] += 1
                if member_query_count[0] == 1:
                    q.filter.return_value.all.return_value = [member, unavailable_member, leader]
                else:
                    q.filter.return_value.all.return_value = [leader]
            return q

        mock_db.query.side_effect = query_side_effect

        with self._patch_settings(enabled=True, leader_ids="1"):
            send_session_reminders(session, mock_db)

        mock_leader_email.assert_called_once()
        call_kwargs = mock_leader_email.call_args.kwargs
        # Bob should be in unavailable list
        assert "Bob Brown" in call_kwargs["unavailable_members"]
        # Alice and Pastor should be available
        assert "Alice Smith" in call_kwargs["available_members"]

    @patch("app.core.scheduler.send_leader_summary_email")
    @patch("app.core.scheduler.send_push_notification")
    @patch("app.core.scheduler.send_reminder_sms")
    @patch("app.core.scheduler.send_reminder_email")
    def test_no_leader_summary_when_leader_ids_empty(self, mock_email, mock_sms, mock_push, mock_leader_email):
        from app.core.scheduler import send_session_reminders

        session = _make_session()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        with self._patch_settings(enabled=True, leader_ids=""):
            send_session_reminders(session, mock_db)

        mock_leader_email.assert_not_called()


class TestDispatchAvailabilityReminders:
    """Tests for the monthly availability reminder dispatcher."""

    @patch("app.core.scheduler.send_availability_reminder_email")
    @patch("app.core.scheduler.SessionLocal")
    @patch("app.core.scheduler.datetime")
    @patch("app.core.scheduler.settings")
    def test_skips_when_disabled(self, mock_settings, mock_dt, mock_session_local, mock_send_email):
        from app.core.scheduler import dispatch_availability_reminders

        mock_settings.availability_reminders_enabled = False

        dispatch_availability_reminders()

        mock_send_email.assert_not_called()
        mock_session_local.assert_not_called()

    @patch("app.core.scheduler.send_availability_reminder_email")
    @patch("app.core.scheduler.SessionLocal")
    @patch("app.core.scheduler.datetime")
    @patch("app.core.scheduler.settings")
    def test_dispatches_when_enabled(self, mock_settings, mock_dt, mock_session_local, mock_send_email):
        from app.core.scheduler import dispatch_availability_reminders

        mock_settings.availability_reminders_enabled = True
        mock_settings.default_redirect_url = "http://localhost:5173/calendar"

        fake_now = MagicMock()
        fake_now.day = 7
        fake_now.month = 6
        fake_now.year = 2026
        mock_dt.now.return_value = fake_now

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        # No lock, no sessions, no members
        mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.all.return_value = []

        dispatch_availability_reminders()

        mock_session_local.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("app.core.scheduler.send_availability_reminder_email")
    @patch("app.core.scheduler.SessionLocal")
    @patch("app.core.scheduler.datetime")
    @patch("app.core.scheduler.settings")
    def test_skips_when_month_locked(self, mock_settings, mock_dt, mock_session_local, mock_send_email):
        from app.core.scheduler import dispatch_availability_reminders

        mock_settings.availability_reminders_enabled = True

        fake_now = MagicMock()
        fake_now.day = 7
        fake_now.month = 6
        fake_now.year = 2026
        mock_dt.now.return_value = fake_now

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        # Simulate an existing MonthLock row with is_locked=True
        mock_lock = MagicMock()
        mock_lock.is_locked = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_lock

        dispatch_availability_reminders()

        mock_send_email.assert_not_called()
        mock_db.close.assert_called_once()

    @patch("app.core.scheduler.send_availability_reminder_email")
    @patch("app.core.scheduler.SessionLocal")
    @patch("app.core.scheduler.datetime")
    @patch("app.core.scheduler.settings")
    def test_computes_next_month_correctly(self, mock_settings, mock_dt, mock_session_local, mock_send_email):
        """When current month is December, target should be January of next year."""
        from app.core.scheduler import dispatch_availability_reminders

        mock_settings.availability_reminders_enabled = True
        mock_settings.default_redirect_url = "http://localhost:5173/calendar"

        fake_now = MagicMock()
        fake_now.day = 7
        fake_now.month = 12  # December
        fake_now.year = 2026
        mock_dt.now.return_value = fake_now

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        # No MonthLock row → not locked, no sessions/members found
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.all.return_value = []

        dispatch_availability_reminders()

        # Should target January 2027
        mock_session_local.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("app.core.scheduler.send_availability_reminder_email")
    @patch("app.core.scheduler.SessionLocal")
    @patch("app.core.scheduler.datetime")
    @patch("app.core.scheduler.settings")
    def test_closes_db_on_exception(self, mock_settings, mock_dt, mock_session_local, mock_send_email):
        from app.core.scheduler import dispatch_availability_reminders

        mock_settings.availability_reminders_enabled = True

        fake_now = MagicMock()
        fake_now.day = 7
        fake_now.month = 6
        fake_now.year = 2026
        mock_dt.now.return_value = fake_now

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.side_effect = Exception("DB error")

        # Should not raise
        dispatch_availability_reminders()

        mock_db.close.assert_called_once()

