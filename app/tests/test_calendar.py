import pytest
from datetime import datetime, timedelta
from models import Session as SessionModel, Assignment, Member
import io

def test_export_pdf(client, db_session):
    # Setup: Create a session and an assignment
    session = SessionModel(
        title="Test Music Service",
        type="program",
        status="active",
        start_time=datetime(2026, 4, 12, 10, 0, 0)
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
        status="active",
        start_time=datetime.now() + timedelta(days=1)
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
        status="active",
        start_time=datetime(2026, 5, 20, 18, 0)
    )
    db_session.add(session)
    db_session.commit()
    
    admin = db_session.query(Member).filter(Member.email == "test@example.com").first()

    save_data = {
        "sessions": [
            {
                "session_id": session.id,
                "session_title": "Target Session",
                "session_date": "2026-05-20",
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
