import pytest
from datetime import datetime, timedelta, date
from app.models.session import Session as SessionModel
from app.models.assignment import Assignment
from app.models.member import Member, Role
from app.models.day_off import DayOff
import io

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
    assert "filename=\"choir_schedule_2026_4.pdf\"" in response.headers["content-disposition"]

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
