from app.core.auth import create_access_token
import pytest

# Reuse fixtures from conftest.py
# client, created_member, created_session

class TestFraudPrevention:

    def test_device_lock_blocks_multiple_members_from_same_device_in_same_session(self, client, created_member, created_session):
        session_id = created_session["id"]
        
        # Create a second member
        member2_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@example.com",
            "phone_number": "+1987654321",
            "password": "password",
        }
        resp = client.post("/members/", json=member2_data)
        assert resp.status_code == 200
        member2 = resp.json()

        # Generate QR Token
        qr_resp = client.get(f"/attendance/qr/token/{session_id}")
        qr_token = qr_resp.json()["token"]

        # Tokens for members
        token1 = create_access_token(data={"sub": created_member["email"]})
        token2 = create_access_token(data={"sub": member2["email"]})

        device_id = "device_123_unique"

        # 1. Member 1 checks in with Device 1 -> SUCCESS
        r1 = client.post(
            f"/attendance/qr/mark?session_id={session_id}&qr_token={qr_token}",
            json={"device_id": device_id},
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert r1.status_code == 200, f"Member 1 failed: {r1.text}"

        # 2. Member 2 checks in with SAME Device -> FAIL (403)
        # Refresh QR token just in case (though expiry is 30s)
        # Usually same QR token works for multiple people within 30s
        r2 = client.post(
            f"/attendance/qr/mark?session_id={session_id}&qr_token={qr_token}",
            json={"device_id": device_id},
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert r2.status_code == 403
        assert "This device has already been used" in r2.json()["detail"]

        # 3. Member 2 checks in with DIFFERENT Device -> SUCCESS
        r3 = client.post(
            f"/attendance/qr/mark?session_id={session_id}&qr_token={qr_token}",
            json={"device_id": "device_456_other"},
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert r3.status_code == 200

    def test_geofencing_blocks_attendance_when_member_is_outside_session_radius(self, client, created_member):
        # Create a session WITH location
        session_data = {
            "title": "Geo Session",
            "type": "program",
            "start_time": "2026-02-15T12:00:00",
            "end_time": "2026-02-15T14:00:00",
            "status": "active",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "radius": 100 # meters
        }
        s_resp = client.post("/sessions/", json=session_data)
        assert s_resp.status_code == 200
        session = s_resp.json()
        session_id = session["id"]

        # DEBUG: Verify session has location
        assert session["latitude"] == 40.7128, f"Latitude not saved: {session}"
        assert session["longitude"] == -74.0060, f"Longitude not saved: {session}"
        assert session["radius"] == 100, f"Radius not saved: {session}"

        # Generate QR
        qr_resp = client.get(f"/attendance/qr/token/{session_id}")
        qr_token = qr_resp.json()["token"]
        auth_token = create_access_token(data={"sub": created_member["email"]})

        # 1. Check in WITHOUT location -> FAIL (403 strict mode)
        r1 = client.post(
            f"/attendance/qr/mark?session_id={session_id}&qr_token={qr_token}",
            json={"device_id": "dev1"}, 
            # No lat/long
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert r1.status_code == 403
        assert "Location access is required" in r1.json()["detail"]

        # 2. Check in OUTSIDE radius -> FAIL
        # 1 degree lat is ~111km. 0.002 deg is ~220m.
        r2 = client.post(
            f"/attendance/qr/mark?session_id={session_id}&qr_token={qr_token}",
            json={"device_id": "dev1", "latitude": 40.7150, "longitude": -74.0060}, # ~240m away
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert r2.status_code == 403
        assert "too far" in r2.json()["detail"]

        # 3. Check in INSIDE radius -> SUCCESS
        r3 = client.post(
            f"/attendance/qr/mark?session_id={session_id}&qr_token={qr_token}",
            json={"device_id": "dev1", "latitude": 40.71281, "longitude": -74.00601}, # Almost exact
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert r3.status_code == 200

    def test_admin_manual_marking_successfully_overrides_and_skips_device_lock_check(self, client, created_member, created_session):
        session_id = created_session["id"]
        
        # Create Member 2
        m2_data = {"first_name": "B", "last_name": "Bee", "email": "b@e.com", "password": "x", "phone_number":"000"}
        member2 = client.post("/members/", json=m2_data).json()

        # Admin (created_member is admin in conftest client) uses "device_admin"
        admin_device = "device_of_admin_XP"

        # 1. Admin marks for Self via Manual -> Should work
        # POST /attendance/ uses AttendanceCreate schema which accepts device_id
        # And endpoint uses Depend(get_admin_member)
        # Note: client fixture overrides get_current_user to return admin
        
        # Wait, POST /attendance/ endpoint signature:
        # def mark_attendance(attendance: schemas.AttendanceCreate, ... current_member=Depends(get_admin_member))
        
        # To test "Marked By Admin", we send marked_by_id = admin_id.
        # But wait, logic: if (marked_by_id is None) OR (marked_by_id == member_id) -> Self Checkin -> Enforce Lock.
        # So we MUST send marked_by_id != member_id.
        
        # First, find admin ID. `created_member` is just a member created via API.
        # The `client` fixture creates a "Test Admin" in DB with email "test@example.com".
        # But `created_member` (fixture) has email "john@example.com".
        # The `client` relies on `get_current_user` returning "test@example.com".
        # So the "Current User" is the generic Test Admin.
        # We need the ID of "Test Admin".
        # We can fetch it via /members/ (since we are admin).
        
        members = client.get("/members/").json()
        admin_user = next(m for m in members if m["email"] == "test@example.com")
        admin_id = admin_user["id"]
        
        # Admin marks for Member 1 (John)
        payload1 = {
            "member_id": created_member["id"],
            "session_id": session_id,
            "submission_type": "manual",
            "marked_by_id": admin_id,
            "device_id": admin_device
        }
        r1 = client.post("/attendance/", json=payload1)
        assert r1.status_code == 200

        # Admin marks for Member 2 (B) using SAME device
        payload2 = {
            "member_id": member2["id"],
            "session_id": session_id,
            "submission_type": "manual",
            "marked_by_id": admin_id, # marked by admin
            "device_id": admin_device # same device
        }
        r2 = client.post("/attendance/", json=payload2)
        assert r2.status_code == 200, f"Admin override failed: {r2.text}"
        
        # Verify both success (no 403).
