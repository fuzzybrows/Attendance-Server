import pytest
from datetime import datetime, timedelta
from app.models.session import Session as SessionModel
from app.models.assignment import Assignment
from app.models.member import Member
import io

def test_export_pdf(client, db_session):
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

def test_get_sync_token(client):
    response = client.post("/calendar/sync/token")
    assert response.status_code == 200
    assert "sync_token" in response.json()
    assert "sync_url" in response.json()

def test_sync_ics(client, db_session):
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

def test_save_schedule(client, db_session):
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

def test_generate_schedule_sunday_role_enforcement(client, db_session):
    """Test that only members with 'Sunday Lead Singer' role are assigned as lead on Sundays."""
    from app.models.member import Role
    # 1. Setup Roles
    lead_role = Role(name="lead_singer", is_choir_role=True)
    sunday_lead_role = Role(name="Sunday Lead Singer", is_choir_role=False)
    db_session.add_all([lead_role, sunday_lead_role])
    db_session.commit()

    # Member A: Has choir role lead_singer but NOT Sunday Lead Singer
    member_a = Member(
        first_name="Regular", last_name="Lead",
        email="regular@test.com", password_hash="hash",
        roles=[lead_role]
    )
    # Member B: Has BOTH roles
    member_b = Member(
        first_name="Sunday", last_name="Pro",
        email="sunday@test.com", password_hash="hash",
        roles=[lead_role, sunday_lead_role]
    )
    db_session.add_all([member_a, member_b])
    db_session.commit()

    # 3. Setup Sessions for a Sunday
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

    # Call generate-schedule (Correct route is /calendar/schedule/generate)
    response = client.post("/calendar/schedule/generate", json={
        "year": 2026,
        "month": 4
    })
    assert response.status_code == 200
    data = response.json()
    
    # Find our Sunday session in the response
    session_data = next((s for s in data["sessions"] if s["id"] == sunday_session.id), None)
    assert session_data is not None
    
    # Find lead_singer assignment
    lead_assignment = next((a for a in session_data["assignments"] if a["role"] == "lead_singer"), None)
    assert lead_assignment is not None
    # Must be Member B
    assert lead_assignment["member_id"] == member_b.id
    assert "Sunday" in lead_assignment["member_name"]
