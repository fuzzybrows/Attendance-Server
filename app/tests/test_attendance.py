"""Tests for attendance endpoints."""


class TestMarkAttendance:
    def test_mark_attendance(self, client, created_member, created_session):
        """Test marking attendance for a member in a session."""
        response = client.post("/attendance/", json={
            "member_id": created_member["id"],
            "session_id": created_session["id"],
            "submission_type": "manual",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["member_id"] == created_member["id"]
        assert data["session_id"] == created_session["id"]

    def test_mark_attendance_duplicate(self, client, created_member, created_session):
        """Test duplicate attendance is rejected."""
        payload = {
            "member_id": created_member["id"],
            "session_id": created_session["id"],
            "submission_type": "manual",
        }
        client.post("/attendance/", json=payload)
        response = client.post("/attendance/", json=payload)
        assert response.status_code == 409
        assert "already marked" in response.json()["detail"]

    def test_mark_attendance_member_not_found(self, client, created_session):
        """Test attendance with non-existent member."""
        response = client.post("/attendance/", json={
            "member_id": 9999,
            "session_id": created_session["id"],
            "submission_type": "manual",
        })
        assert response.status_code == 404
        assert "Member" in response.json()["detail"]

    def test_mark_attendance_session_not_found(self, client, created_member):
        """Test attendance with non-existent session."""
        response = client.post("/attendance/", json={
            "member_id": created_member["id"],
            "session_id": 9999,
            "submission_type": "manual",
        })
        assert response.status_code == 404
        assert "Session" in response.json()["detail"]

    def test_mark_attendance_with_gps(self, client, created_member, created_session):
        """Test marking attendance with GPS coordinates."""
        response = client.post("/attendance/", json={
            "member_id": created_member["id"],
            "session_id": created_session["id"],
            "submission_type": "manual",
            "latitude": 29.7604,
            "longitude": -95.3698,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["latitude"] == 29.7604
        assert data["longitude"] == -95.3698


class TestReadAttendance:
    def test_read_attendance_by_session(self, client, created_member, created_session):
        """Test reading attendance records for a session."""
        client.post("/attendance/", json={
            "member_id": created_member["id"],
            "session_id": created_session["id"],
            "submission_type": "manual",
        })
        response = client.get(f"/attendance/session/{created_session['id']}")
        assert response.status_code == 200
        records = response.json()
        assert len(records) == 1

    def test_read_attendance_by_member(self, client, created_member, created_session):
        """Test reading attendance records for a member."""
        client.post("/attendance/", json={
            "member_id": created_member["id"],
            "session_id": created_session["id"],
            "submission_type": "manual",
        })
        response = client.get(f"/attendance/member/{created_member['id']}")
        assert response.status_code == 200
        records = response.json()
        assert len(records) == 1
        assert "session" in records[0]  # Should include session details


class TestDeleteAttendance:
    def test_delete_attendance(self, client, created_member, created_session):
        """Test deleting an attendance record."""
        create_resp = client.post("/attendance/", json={
            "member_id": created_member["id"],
            "session_id": created_session["id"],
            "submission_type": "manual",
        })
        att_id = create_resp.json()["id"]

        response = client.delete(f"/attendance/{att_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    def test_delete_attendance_not_found(self, client):
        """Test deleting non-existent attendance."""
        response = client.delete("/attendance/9999")
        assert response.status_code == 404


class TestAttendanceStats:
    def test_stats_empty(self, client):
        """Test stats with no data."""
        response = client.get("/attendance/stats")
        assert response.status_code == 200
        # Now returns stats for Test Admin
        stats = response.json()
        assert len(stats) == 1
        assert stats[0]["name"] == "Test Admin"
        assert stats[0]["total_sessions"] == 0

    def test_stats_with_data(self, client, created_member, created_session):
        """Test stats calculation."""
        client.post("/attendance/", json={
            "member_id": created_member["id"],
            "session_id": created_session["id"],
            "submission_type": "manual",
        })
        response = client.get("/attendance/stats")
        assert response.status_code == 200
        stats = response.json()
        stats = response.json()
        # Should be Test Admin + Created Member = 2
        assert len(stats) == 2
        
        # Find stats for created member
        member_stats = next(s for s in stats if s["member_id"] == created_member["id"])
        
        assert member_stats["total_sessions"] == 1
        # Session is in past (Feb 15) vs Now (Feb 16+), so it should be late
        assert member_stats["late_count"] == 1
        assert member_stats["prompt_count"] == 0


class TestBulkDeleteAttendance:
    def test_bulk_delete_attendance(self, client, created_member, created_session):
        """Test bulk deleting attendance records."""
        # Create a second session for a second attendance record
        session2 = client.post("/sessions/", json={
            "title": "Another Session",
            "type": "rehearsal",
            "start_time": "2026-02-16T10:00:00",
            "end_time": "2026-02-16T12:00:00",
            "status": "active",
        }).json()

        r1 = client.post("/attendance/", json={
            "member_id": created_member["id"],
            "session_id": created_session["id"],
            "submission_type": "manual",
        })
        r2 = client.post("/attendance/", json={
            "member_id": created_member["id"],
            "session_id": session2["id"],
            "submission_type": "manual",
        })

        ids = [r1.json()["id"], r2.json()["id"]]
        response = client.post("/attendance/bulk-delete", json={"ids": ids})
        assert response.status_code == 200
        assert response.json()["count"] == 2

    def test_bulk_delete_attendance_empty(self, client):
        """Test bulk delete with no IDs returns 400."""
        response = client.post("/attendance/bulk-delete", json={"ids": []})
        assert response.status_code == 400


class TestMemberAttendance:
    def test_read_member_attendance_empty(self, client, created_member):
        """Test reading attendance for a member with no records."""
        response = client.get(f"/attendance/member/{created_member['id']}")
        assert response.status_code == 200
        assert response.json() == []

