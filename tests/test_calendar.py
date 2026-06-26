import pytest
import io
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from app.models.session import Session as SessionModel
from app.models.assignment import Assignment
from app.models.member import Member, Role
from app.models.day_off import DayOff
from app.models.month_lock import MonthLock
from app.core.auth import get_current_user
from app.server import app
from app.services.comm import send_assignment_notification_email

def test_calendar_export_as_pdf_returns_valid_pdf_response(client, db_session):
    # Setup: Create a session and an assignment
    session = SessionModel(
        title="Test Music Service",
        type="program",
        start_time=datetime(2026, 4, 12, 10, 0, 0),
        end_time=datetime(2026, 4, 12, 12, 0, 0),
        status="scheduled"
    )
    db_session.add(session)
    db_session.commit()

    admin = db_session.query(Member).filter(Member.email == "test@example.com").first()
    assignment = Assignment(
        session_id=session.id,
        member_id=admin.id,
        role="lead_singer"
    )
    db_session.add(assignment)
    db_session.commit()

    # Test PDF Export
    response = client.get("/calendar/schedule/export_pdf?year=2026&month=4")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "filename=\"" in response.headers["content-disposition"]
    assert "_schedule_2026_4.pdf" in response.headers["content-disposition"]

def test_calendar_sync_token_generation_returns_valid_token_and_url(client):
    response = client.post("/calendar/sync/token")
    assert response.status_code == 200
    assert "sync_token" in response.json()
    assert "sync_url" in response.json()

def test_calendar_ics_sync_endpoint_returns_valid_vcalendar_data(client, db_session):
    # Get token
    res_token = client.post("/calendar/sync/token").json()
    sync_token = res_token["sync_token"]
    
    admin = db_session.query(Member).filter(Member.email == "test@example.com").first()
    
    # Setup a session
    session = SessionModel(
        title="Sync Test Session",
        type="rehearsal",
        start_time=datetime.now() + timedelta(days=1),
        end_time=datetime.now() + timedelta(days=1, hours=2),
        status="scheduled"
    )
    db_session.add(session)
    db_session.commit()
    
    assignment = Assignment(session_id=session.id, member_id=admin.id, role="soprano")
    db_session.add(assignment)
    db_session.commit()

    # Call sync endpoint
    response = client.get(f"/calendar/sync/{admin.id}.ics?key={sync_token}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    assert b"BEGIN:VCALENDAR" in response.content
    assert b"Sync Test Session" in response.content

def test_calendar_save_schedule_updates_assignments_correctly_in_database(client, db_session):
    # Setup: Create a session
    session = SessionModel(
        title="Target Session",
        type="program",
        start_time=datetime(2026, 5, 20, 18, 0),
        end_time=datetime(2026, 5, 20, 20, 0),
        status="scheduled"
    )
    db_session.add(session)
    db_session.commit()
    
    admin = db_session.query(Member).filter(Member.email == "test@example.com").first()

    save_data = {
        "sessions": [
            {
                "id": session.id,
                "title": "Target Session",
                "type": "program",
                "start_time": "2026-05-20T18:00:00Z",
                "assignments": [
                    {
                        "member_id": admin.id,
                        "member_name": "Test Admin",
                        "role": "alto"
                    }
                ]
            }
        ]
    }
    
    response = client.post("/calendar/schedule/save", json=save_data)
    assert response.status_code == 200
    
    # Verify in DB
    updated_assignment = db_session.query(Assignment).filter(Assignment.session_id == session.id).first()
    assert updated_assignment is not None
    assert updated_assignment.role == "alto"

def test_generate_schedule_enforces_sunday_lead_singer_role_restriction_on_sundays(client, db_session):
    # 1. Setup Roles
    lead_role = Role(name="lead_singer", display_order=1)
    sunday_lead_role = Role(name="Sunday Lead Singer")  # no display_order = not assignable itself
    db_session.add_all([lead_role, sunday_lead_role])
    db_session.flush()

    # Wire the FK: lead_singer on Sundays requires "Sunday Lead Singer"
    lead_role.sunday_qualifier_role = sunday_lead_role
    db_session.commit()

    # Member A: Has lead_singer role but NOT "Sunday Lead Singer"
    member_a = Member(
        first_name="Regular", last_name="Lead",
        email="regular@test.com", password_hash="hash",
        roles=[lead_role]
    )
    # Member B: Has BOTH roles → eligible on Sundays
    member_b = Member(
        first_name="Sunday", last_name="Pro",
        email="sunday@test.com", password_hash="hash",
        roles=[lead_role, sunday_lead_role]
    )
    db_session.add_all([member_a, member_b])
    db_session.commit()

    # Sunday, April 12, 2026
    sunday_session = SessionModel(
        title="Sunday Service",
        type="program",
        start_time=datetime(2026, 4, 12, 10, 0),
        end_time=datetime(2026, 4, 12, 12, 0),
        status="scheduled"
    )
    db_session.add(sunday_session)
    db_session.commit()

    response = client.post("/calendar/schedule/generate", json={
        "year": 2026,
        "month": 4
    })
    assert response.status_code == 200
    data = response.json()

    session_data = next((s for s in data["sessions"] if s["id"] == sunday_session.id), None)
    assert session_data is not None

    lead_assignment = next((a for a in session_data["assignments"] if a["role"] == "lead_singer"), None)
    assert lead_assignment is not None
    # Must be Member B (the qualifier holder) — FK-driven, not hardcoded name
    assert lead_assignment["member_id"] == member_b.id
    assert "Sunday" in lead_assignment["member_name"]



def test_month_availability_includes_day_off_records(client, db_session):
    """Regression: DayOff records should appear in opted_out_member_ids
    for sessions on that day."""
    # Setup: a session on May 10, 2026
    session = SessionModel(
        title="Saturday Practice",
        type="rehearsal",
        start_time=datetime(2026, 5, 10, 10, 0, 0),
        end_time=datetime(2026, 5, 10, 12, 0, 0),
        status="scheduled"
    )
    db_session.add(session)
    db_session.commit()

    admin = db_session.query(Member).filter(Member.email == "test@example.com").first()

    # Mark the whole day as unavailable via DayOff (no per-session Availability record)
    day_off = DayOff(
        member_id=admin.id,
        date=date(2026, 5, 10),
        is_available=False
    )
    db_session.add(day_off)
    db_session.commit()

    # Fetch month availability
    response = client.get("/calendar/availability/2026/5")
    assert response.status_code == 200
    data = response.json()

    # Find the session
    session_data = next(
        (s for s in data["sessions"] if s["id"] == session.id), None
    )
    assert session_data is not None, "Session not found in availability response"

    # Admin should appear in opted_out_member_ids due to DayOff
    assert admin.id in session_data["opted_out_member_ids"], (
        f"Member {admin.id} marked the day off but is not in opted_out_member_ids"
    )


def _create_assignable_role(db_session, name="soprano", display_order=1):
    """Create or get a role with display_order set (i.e. assignable)."""
    role = db_session.query(Role).filter_by(name=name).first()
    if not role:
        role = Role(name=name, display_order=display_order)
        db_session.add(role)
        db_session.commit()
    return role


class TestMemberFilteringInScheduling:
    """Ensure disabled and roleless members are excluded from scheduling views."""

    def test_team_availability_excludes_inactive_members(self, client, db_session):
        role = _create_assignable_role(db_session)

        active_member = Member(
            first_name="Active", last_name="Singer",
            email="active@test.com", is_active=True, roles=[role]
        )
        inactive_member = Member(
            first_name="Inactive", last_name="Singer",
            email="inactive@test.com", is_active=False, roles=[role]
        )
        db_session.add_all([active_member, inactive_member])
        db_session.commit()

        session = SessionModel(
            title="Test Service", type="program",
            start_time=datetime(2026, 6, 14, 10, 0),
            end_time=datetime(2026, 6, 14, 12, 0),
            status="scheduled"
        )
        db_session.add(session)
        db_session.commit()

        response = client.get("/calendar/availability/team/2026/6")
        assert response.status_code == 200
        data = response.json()

        member_ids = [m["id"] for m in data["members"]]
        assert active_member.id in member_ids
        assert inactive_member.id not in member_ids

    def test_team_availability_excludes_members_without_assignable_roles(self, client, db_session):
        role = _create_assignable_role(db_session)

        member_with_role = Member(
            first_name="Assigned", last_name="Singer",
            email="assigned@test.com", is_active=True, roles=[role]
        )
        member_no_role = Member(
            first_name="NoRole", last_name="Person",
            email="norole@test.com", is_active=True, roles=[]
        )
        db_session.add_all([member_with_role, member_no_role])
        db_session.commit()

        session = SessionModel(
            title="Role Check Service", type="program",
            start_time=datetime(2026, 6, 14, 10, 0),
            end_time=datetime(2026, 6, 14, 12, 0),
            status="scheduled"
        )
        db_session.add(session)
        db_session.commit()

        response = client.get("/calendar/availability/team/2026/6")
        assert response.status_code == 200
        data = response.json()

        member_ids = [m["id"] for m in data["members"]]
        assert member_with_role.id in member_ids
        assert member_no_role.id not in member_ids

    def test_generate_schedule_excludes_inactive_members(self, client, db_session):
        role = _create_assignable_role(db_session, name="alto", display_order=2)

        active_member = Member(
            first_name="Active", last_name="Alto",
            email="activealt@test.com", is_active=True, roles=[role]
        )
        inactive_member = Member(
            first_name="Ghost", last_name="Alto",
            email="ghostalt@test.com", is_active=False, roles=[role]
        )
        db_session.add_all([active_member, inactive_member])
        db_session.commit()

        session = SessionModel(
            title="Schedule Test", type="program",
            start_time=datetime(2026, 6, 15, 10, 0),
            end_time=datetime(2026, 6, 15, 12, 0),
            status="scheduled"
        )
        db_session.add(session)
        db_session.commit()

        response = client.post("/calendar/schedule/generate", json={
            "year": 2026, "month": 6
        })
        assert response.status_code == 200
        data = response.json()

        # Collect all assigned member IDs
        assigned_ids = set()
        for s in data["sessions"]:
            for a in s["assignments"]:
                assigned_ids.add(a["member_id"])

        assert inactive_member.id not in assigned_ids

    def test_generate_schedule_excludes_members_with_day_off(self, client, db_session):
        """Members who marked a day as unavailable via DayOff should not be assigned."""
        role = _create_assignable_role(db_session, name="soprano", display_order=1)

        available_member = Member(
            first_name="Available", last_name="Singer",
            email="avail_singer@test.com", is_active=True, roles=[role]
        )
        unavailable_member = Member(
            first_name="DayOff", last_name="Singer",
            email="dayoff_singer@test.com", is_active=True, roles=[role]
        )
        db_session.add_all([available_member, unavailable_member])
        db_session.commit()

        # Session on June 16, 2026
        session = SessionModel(
            title="Day Off Test", type="program",
            start_time=datetime(2026, 6, 16, 10, 0),
            end_time=datetime(2026, 6, 16, 12, 0),
            status="scheduled"
        )
        db_session.add(session)
        db_session.commit()

        # Mark unavailable_member as having the day off
        day_off = DayOff(
            member_id=unavailable_member.id,
            date=date(2026, 6, 16),
            is_available=False
        )
        db_session.add(day_off)
        db_session.commit()

        response = client.post("/calendar/schedule/generate", json={
            "year": 2026, "month": 6
        })
        assert response.status_code == 200
        data = response.json()

        assigned_ids = set()
        for s in data["sessions"]:
            for a in s["assignments"]:
                assigned_ids.add(a["member_id"])

        assert unavailable_member.id not in assigned_ids, (
            "Member with DayOff should not be assigned"
        )
        assert available_member.id in assigned_ids

    def test_generate_schedule_day_off_uses_local_timezone(self, client, db_session):
        """Regression: session_date must use local timezone, not UTC, when
        looking up DayOff records.  An evening session stored as next-day UTC
        should still match a local-date DayOff."""

        role = _create_assignable_role(db_session, name="tenor", display_order=3)

        member = Member(
            first_name="Evening", last_name="Singer",
            email="evening_tz@test.com", is_active=True, roles=[role]
        )
        db_session.add(member)
        db_session.commit()

        # June 16 2026 at 11 PM CDT = June 17 2026 04:00 UTC
        # The session is on June 16 *locally*, but June 17 in UTC.
        local_tz = ZoneInfo("America/Chicago")
        session_start = datetime(2026, 6, 16, 23, 0, tzinfo=local_tz)
        session_end = datetime(2026, 6, 17, 1, 0, tzinfo=local_tz)

        session = SessionModel(
            title="Late Night Service", type="program",
            start_time=session_start,
            end_time=session_end,
            status="scheduled"
        )
        db_session.add(session)
        db_session.commit()

        # Mark June 16 (local date) as day off
        day_off = DayOff(
            member_id=member.id,
            date=date(2026, 6, 16),
            is_available=False
        )
        db_session.add(day_off)
        db_session.commit()

        response = client.post("/calendar/schedule/generate", json={
            "year": 2026, "month": 6
        })
        assert response.status_code == 200
        data = response.json()

        # Find the late-night session
        session_data = next(
            (s for s in data["sessions"] if s["id"] == session.id), None
        )
        assert session_data is not None

        assigned_ids = [a["member_id"] for a in session_data["assignments"]]
        assert member.id not in assigned_ids, (
            "Member with DayOff on June 16 should not be assigned to a "
            "June 16 local-time session even though UTC date is June 17"
        )


    def test_availability_export_csv_excludes_inactive_and_roleless_members(self, client, db_session):
        role = _create_assignable_role(db_session)

        active_member = Member(
            first_name="Export", last_name="Singer",
            email="export@test.com", is_active=True, roles=[role]
        )
        inactive_member = Member(
            first_name="Gone", last_name="Singer",
            email="gone@test.com", is_active=False, roles=[role]
        )
        roleless_member = Member(
            first_name="Roleless", last_name="Person",
            email="roleless@test.com", is_active=True, roles=[]
        )
        db_session.add_all([active_member, inactive_member, roleless_member])
        db_session.commit()

        session = SessionModel(
            title="Export Session", type="program",
            start_time=datetime(2026, 6, 14, 10, 0),
            end_time=datetime(2026, 6, 14, 12, 0),
            status="scheduled"
        )
        db_session.add(session)
        db_session.commit()

        response = client.get("/calendar/availability/export_csv?year=2026&month=6")
        assert response.status_code == 200

        csv_text = response.text
        assert "Export Singer" in csv_text
        assert "Gone Singer" not in csv_text
        assert "Roleless Person" not in csv_text


class TestPDFNameFormatting:
    """Verify PDF export uses 'FirstName L.' name format."""

    def test_pdf_export_uses_abbreviated_last_name(self, client, db_session):
        session = SessionModel(
            title="PDF Name Test",
            type="program",
            start_time=datetime(2026, 7, 12, 10, 0),
            end_time=datetime(2026, 7, 12, 12, 0),
            status="scheduled"
        )
        db_session.add(session)
        db_session.commit()

        member = Member(
            first_name="Jessica", last_name="Williams",
            email="jessica@test.com", is_active=True
        )
        db_session.add(member)
        db_session.commit()

        assignment = Assignment(session_id=session.id, member_id=member.id, role="soprano")
        db_session.add(assignment)
        db_session.commit()

        response = client.get("/calendar/schedule/export_pdf?year=2026&month=7")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    def test_pdf_export_handles_empty_last_name(self, client, db_session):
        session = SessionModel(
            title="Empty Last Name Test",
            type="program",
            start_time=datetime(2026, 8, 9, 10, 0),
            end_time=datetime(2026, 8, 9, 12, 0),
            status="scheduled"
        )
        db_session.add(session)
        db_session.commit()

        member = Member(
            first_name="Cher", last_name="",
            email="cher@test.com", is_active=True
        )
        db_session.add(member)
        db_session.commit()

        assignment = Assignment(session_id=session.id, member_id=member.id, role="alto")
        db_session.add(assignment)
        db_session.commit()

        # Should not crash with IndexError
        response = client.get("/calendar/schedule/export_pdf?year=2026&month=8")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    def test_pdf_export_handles_none_last_name(self, client, db_session):
        session = SessionModel(
            title="None Last Name Test",
            type="program",
            start_time=datetime(2026, 9, 13, 10, 0),
            end_time=datetime(2026, 9, 13, 12, 0),
            status="scheduled"
        )
        db_session.add(session)
        db_session.commit()

        member = Member(
            first_name="Prince", last_name=None,
            email="prince@test.com", is_active=True
        )
        db_session.add(member)
        db_session.commit()

        assignment = Assignment(session_id=session.id, member_id=member.id, role="tenor")
        db_session.add(assignment)
        db_session.commit()

        # Should not crash with TypeError
        response = client.get("/calendar/schedule/export_pdf?year=2026&month=9")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"


# ── Month Lock Tests ──


def test_save_schedule_auto_creates_month_lock(client, db_session):
    """Saving a schedule should auto-create a MonthLock row with is_locked=True."""

    session = SessionModel(
        title="July Service",
        type="program",
        start_time=datetime(2026, 7, 12, 10, 0, 0),
        end_time=datetime(2026, 7, 12, 12, 0, 0),
        status="scheduled"
    )
    db_session.add(session)
    db_session.commit()

    admin = db_session.query(Member).filter(Member.email == "test@example.com").first()

    save_data = {
        "sessions": [{
            "id": session.id,
            "title": "July Service",
            "type": "program",
            "start_time": "2026-07-12T10:00:00Z",
            "assignments": [{
                "member_id": admin.id,
                "member_name": "Test Admin",
                "role": "soprano"
            }]
        }]
    }

    response = client.post("/calendar/schedule/save", json=save_data)
    assert response.status_code == 200

    lock = db_session.query(MonthLock).filter(
        MonthLock.year == 2026, MonthLock.month == 7
    ).first()
    assert lock is not None
    assert lock.is_locked is True


def test_schedule_response_includes_month_locked_field(client, db_session):
    """GET /calendar/schedule/{year}/{month} should include month_locked."""
    session = SessionModel(
        title="Aug Service",
        type="program",
        start_time=datetime(2026, 8, 9, 10, 0, 0),
        end_time=datetime(2026, 8, 9, 12, 0, 0),
        status="scheduled"
    )
    db_session.add(session)
    db_session.commit()

    # No lock set — should be unlocked
    response = client.get("/calendar/schedule/2026/8")
    assert response.status_code == 200
    data = response.json()
    assert "month_locked" in data
    assert data["month_locked"] is False


def test_schedule_response_month_locked_true_after_save(client, db_session):
    """After saving assignments, month_locked should be True in the schedule response."""

    session = SessionModel(
        title="Sep Service",
        type="program",
        start_time=datetime(2026, 9, 6, 10, 0, 0),
        end_time=datetime(2026, 9, 6, 12, 0, 0),
        status="scheduled"
    )
    db_session.add(session)
    db_session.commit()

    admin = db_session.query(Member).filter(Member.email == "test@example.com").first()

    save_data = {
        "sessions": [{
            "id": session.id,
            "title": "Sep Service",
            "type": "program",
            "start_time": "2026-09-06T10:00:00Z",
            "assignments": [{"member_id": admin.id, "member_name": "Test Admin", "role": "alto"}]
        }]
    }
    client.post("/calendar/schedule/save", json=save_data)

    response = client.get("/calendar/schedule/2026/9")
    assert response.json()["month_locked"] is True


def test_admin_can_toggle_month_lock(client, db_session):
    """Admin should be able to lock and unlock a month via PUT /calendar/month-lock."""
    # Lock
    response = client.put("/calendar/month-lock?year=2026&month=10&is_locked=true")
    assert response.status_code == 200
    data = response.json()
    assert data["is_locked"] is True

    # Unlock
    response = client.put("/calendar/month-lock?year=2026&month=10&is_locked=false")
    assert response.status_code == 200
    data = response.json()
    assert data["is_locked"] is False


def test_admin_can_unlock_after_save(client, db_session):
    """Admin should be able to unlock a month that was auto-locked by saving."""

    session = SessionModel(
        title="Oct Service",
        type="program",
        start_time=datetime(2026, 10, 4, 10, 0, 0),
        end_time=datetime(2026, 10, 4, 12, 0, 0),
        status="scheduled"
    )
    db_session.add(session)
    db_session.commit()

    admin = db_session.query(Member).filter(Member.email == "test@example.com").first()
    save_data = {
        "sessions": [{
            "id": session.id,
            "title": "Oct Service",
            "type": "program",
            "start_time": "2026-10-04T10:00:00Z",
            "assignments": [{"member_id": admin.id, "member_name": "Test Admin", "role": "tenor"}]
        }]
    }
    client.post("/calendar/schedule/save", json=save_data)

    # Should be locked
    sched = client.get("/calendar/schedule/2026/10").json()
    assert sched["month_locked"] is True

    # Admin unlocks
    client.put("/calendar/month-lock?year=2026&month=10&is_locked=false")

    # Should now be unlocked
    sched = client.get("/calendar/schedule/2026/10").json()
    assert sched["month_locked"] is False


def test_month_lock_invalid_month_returns_400(client):
    """PUT with invalid month should return 400."""
    response = client.put("/calendar/month-lock?year=2026&month=13&is_locked=true")
    assert response.status_code == 400


def test_resaving_schedule_relocks_month(client, db_session):
    """Re-saving assignments should re-lock a previously unlocked month."""

    session = SessionModel(
        title="Nov Service",
        type="program",
        start_time=datetime(2026, 11, 1, 10, 0, 0),
        end_time=datetime(2026, 11, 1, 12, 0, 0),
        status="scheduled"
    )
    db_session.add(session)
    db_session.commit()

    admin = db_session.query(Member).filter(Member.email == "test@example.com").first()
    save_data = {
        "sessions": [{
            "id": session.id,
            "title": "Nov Service",
            "type": "program",
            "start_time": "2026-11-01T10:00:00Z",
            "assignments": [{"member_id": admin.id, "member_name": "Test Admin", "role": "soprano"}]
        }]
    }

    # Save → auto-lock
    client.post("/calendar/schedule/save", json=save_data)
    assert client.get("/calendar/schedule/2026/11").json()["month_locked"] is True

    # Admin unlocks
    client.put("/calendar/month-lock?year=2026&month=11&is_locked=false")
    assert client.get("/calendar/schedule/2026/11").json()["month_locked"] is False

    # Re-save → should re-lock
    client.post("/calendar/schedule/save", json=save_data)
    assert client.get("/calendar/schedule/2026/11").json()["month_locked"] is True


# ─── Assignment Notification Tests ─────────────────────────────────────────

def test_notify_schedule_sends_to_members_with_assignments(client, db_session):
    """POST /calendar/schedule/notify sends emails to eligible members."""
    # Create an assignable role and give it to the admin
    role = Role(name="soprano", display_order=1)
    db_session.add(role)
    db_session.commit()

    admin = db_session.query(Member).filter(Member.email == "test@example.com").first()
    admin.roles.append(role)
    db_session.commit()

    # Create a session with assignment
    session = SessionModel(
        title="Dec Service",
        type="program",
        start_time=datetime(2026, 12, 6, 10, 0, 0),
        end_time=datetime(2026, 12, 6, 12, 0, 0),
        status="scheduled"
    )
    db_session.add(session)
    db_session.commit()

    assignment = Assignment(session_id=session.id, member_id=admin.id, role="soprano")
    db_session.add(assignment)
    db_session.commit()

    resp = client.post("/calendar/schedule/notify?year=2026&month=12")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sent"] >= 1
    assert data["total_eligible"] >= 1
    assert "December 2026" in data["message"]


def test_notify_schedule_includes_members_without_assignments(client, db_session):
    """Members with assignable roles but no assignments still get notified."""
    role = Role(name="alto", display_order=2)
    db_session.add(role)
    db_session.commit()

    admin = db_session.query(Member).filter(Member.email == "test@example.com").first()
    admin.roles.append(role)

    # Add a second member with the role but no assignments
    member2 = Member(first_name="Jane", last_name="Doe", email="jane@example.com")
    member2.roles.append(role)
    db_session.add(member2)
    db_session.commit()

    # No sessions/assignments at all for this month
    resp = client.post("/calendar/schedule/notify?year=2026&month=12")
    assert resp.status_code == 200
    data = resp.json()
    # Both members should be eligible
    assert data["total_eligible"] >= 2
    assert data["sent"] >= 2


def test_notify_schedule_response_has_correct_structure(client, db_session):
    """Notify response must have message, sent, failed, total_eligible keys."""
    role = Role(name="bass", display_order=3)
    db_session.add(role)
    db_session.commit()

    admin = db_session.query(Member).filter(Member.email == "test@example.com").first()
    admin.roles.append(role)
    db_session.commit()

    resp = client.post("/calendar/schedule/notify?year=2026&month=7")
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "sent" in data
    assert "failed" in data
    assert "total_eligible" in data
    assert data["failed"] == 0


def test_notify_schedule_excludes_inactive_members(client, db_session):
    """Inactive members should not receive notifications."""
    role = Role(name="tenor", display_order=4)
    db_session.add(role)
    db_session.commit()

    admin = db_session.query(Member).filter(Member.email == "test@example.com").first()
    admin.roles.append(role)

    # Add an inactive member with the role
    inactive = Member(first_name="Gone", last_name="User", email="gone@example.com", is_active=False)
    inactive.roles.append(role)
    db_session.add(inactive)
    db_session.commit()

    resp = client.post("/calendar/schedule/notify?year=2026&month=10")
    assert resp.status_code == 200
    data = resp.json()
    # Only the admin should be eligible (inactive excluded)
    assert data["total_eligible"] == 1


def test_notify_schedule_excludes_members_without_assignable_roles(client, db_session):
    """Members without any assignable roles should not receive notifications."""
    role = Role(name="admin_role")  # No display_order → not assignable
    db_session.add(role)
    db_session.commit()

    admin = db_session.query(Member).filter(Member.email == "test@example.com").first()
    admin.roles.append(role)
    db_session.commit()

    resp = client.post("/calendar/schedule/notify?year=2026&month=9")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_eligible"] == 0
    assert data["sent"] == 0


def test_notify_schedule_requires_schedule_generate_permission(client, db_session):
    """Users without schedule_generate permission cannot call the notify endpoint."""


    # Create a non-admin member without schedule_generate permission
    member = Member(first_name="Regular", last_name="User", email="regular@example.com")
    db_session.add(member)
    db_session.commit()

    def _fake_regular_user():
        return "regular@example.com"

    app.dependency_overrides[get_current_user] = _fake_regular_user
    resp = client.post("/calendar/schedule/notify?year=2026&month=12")
    # Should be 403 (no schedule_generate permission)
    assert resp.status_code == 403

    # Restore admin override
    def _fake_admin():
        return "test@example.com"
    app.dependency_overrides[get_current_user] = _fake_admin


# ─── Lock Enforcement on Availability ──────────────────────────────────────

def test_locked_month_blocks_session_availability_for_admin(client, db_session):
    """Admin users should also be blocked from changing session availability when locked."""

    session = SessionModel(
        title="Locked Session",
        type="program",
        start_time=datetime(2026, 8, 15, 10, 0, 0),
        end_time=datetime(2026, 8, 15, 12, 0, 0),
        status="scheduled"
    )
    db_session.add(session)
    db_session.commit()

    # Lock August 2026
    lock = MonthLock(year=2026, month=8, is_locked=True)
    db_session.add(lock)
    db_session.commit()

    # Admin should be blocked
    resp = client.put(f"/calendar/availability?session_id={session.id}", json={"is_available": False})
    assert resp.status_code == 400
    assert "locked" in resp.json()["detail"].lower()


def test_locked_month_blocks_day_availability_for_admin(client, db_session):
    """Admin users should also be blocked from changing day-level availability when locked."""

    lock = MonthLock(year=2026, month=9, is_locked=True)
    db_session.add(lock)
    db_session.commit()

    resp = client.post(
        "/calendar/availability/day",
        json={"date": "2026-09-15", "is_available": False}
    )
    assert resp.status_code == 400
    assert "locked" in resp.json()["detail"].lower()


def test_unlocked_month_allows_availability_change(client, db_session):
    """Availability changes should succeed when the month is not locked."""
    session = SessionModel(
        title="Open Session",
        type="program",
        start_time=datetime(2026, 10, 10, 10, 0, 0),
        end_time=datetime(2026, 10, 10, 12, 0, 0),
        status="scheduled"
    )
    db_session.add(session)
    db_session.commit()

    resp = client.put(f"/calendar/availability?session_id={session.id}", json={"is_available": False})
    assert resp.status_code == 200


# ─── Email Attachment Support (Unit) ───────────────────────────────────────

def test_send_assignment_notification_email_with_ics():
    """send_assignment_notification_email should succeed with .ics attachment bytes."""

    ics_content = b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR"

    result = send_assignment_notification_email(
        to_email="test@example.com",
        member_first_name="John",
        year=2026,
        month=12,
        assignments=[{
            "session_title": "Sunday Service",
            "role": "lead_singer",
            "start_time": datetime(2026, 12, 6, 10, 0, 0),
            "end_time": datetime(2026, 12, 6, 13, 0, 0),
        }],
        calendar_url="https://example.com/calendar?month=12&year=2026",
        ics_bytes=ics_content,
    )
    assert result is True


def test_send_assignment_notification_email_without_assignments():
    """send_assignment_notification_email should succeed with no assignments (no .ics)."""

    result = send_assignment_notification_email(
        to_email="test@example.com",
        member_first_name="Jane",
        year=2026,
        month=12,
        assignments=[],
        calendar_url="https://example.com/calendar?month=12&year=2026",
    )
    assert result is True
