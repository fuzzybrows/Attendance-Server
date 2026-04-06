"""Tests for session CRUD endpoints."""


class TestCreateSession:
    def test_create_session(self, client, sample_session_data):
        """Test creating a new session."""
        response = client.post("/sessions/", json=sample_session_data)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == sample_session_data["title"]
        assert data["type"] == sample_session_data["type"]
        assert data["status"] == "active"
        assert "id" in data

    def test_create_session_missing_fields(self, client):
        """Test creating a session with missing required fields."""
        response = client.post("/sessions/", json={"title": "Test"})
        assert response.status_code == 422


class TestReadSessions:
    def test_read_sessions_empty(self, client):
        """Test reading sessions when none exist."""
        response = client.get("/sessions/")
        assert response.status_code == 200
        assert response.json() == []

    def test_read_sessions(self, client, created_session):
        """Test reading all sessions."""
        response = client.get("/sessions/")
        assert response.status_code == 200
        sessions = response.json()
        assert len(sessions) == 1
        assert sessions[0]["title"] == created_session["title"]


class TestUpdateSession:
    def test_update_session(self, client, created_session):
        """Test updating a session."""
        response = client.patch(f"/sessions/{created_session['id']}", json={
            "title": "Updated Rehearsal",
        })
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Rehearsal"

    def test_update_session_not_found(self, client):
        """Test updating a non-existent session."""
        response = client.patch("/sessions/9999", json={"title": "Test"})
        assert response.status_code == 404


class TestDeleteSession:
    def test_delete_session(self, client, created_session):
        """Test deleting a session."""
        response = client.delete(f"/sessions/{created_session['id']}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

        # Verify it's gone
        response = client.get("/sessions/")
        assert len(response.json()) == 0

    def test_delete_session_not_found(self, client):
        """Test deleting a non-existent session."""
        response = client.delete("/sessions/9999")
        assert response.status_code == 404

    def test_bulk_delete_sessions(self, client):
        """Test bulk deleting sessions."""
        # Create multiple sessions
        for i in range(3):
            client.post("/sessions/", json={
                "title": f"Session {i}",
                "type": "rehearsal",
                "status": "active",
                "start_time": "2026-02-15T10:00:00",
                "end_time": "2026-02-15T12:00:00",
            })

        sessions = client.get("/sessions/").json()
        ids = [s["id"] for s in sessions]

        response = client.post("/sessions/bulk-delete", json={"ids": ids})
        assert response.status_code == 200
        assert response.json()["count"] == 3

    def test_bulk_delete_empty_ids(self, client):
        """Test bulk delete with empty IDs list."""
        response = client.post("/sessions/bulk-delete", json={"ids": []})
        assert response.status_code == 400
