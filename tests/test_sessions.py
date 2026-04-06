"""Tests for session CRUD endpoints."""


class TestCreateSession:
    def test_create_session_successfully_persists_valid_session_data(self, client, sample_session_data):
        response = client.post("/sessions/", json=sample_session_data)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == sample_session_data["title"]
        assert data["type"] == sample_session_data["type"]
        assert data["status"] == "active"
        assert "id" in data

    def test_create_session_fails_and_returns_422_when_required_fields_are_missing(self, client):
        response = client.post("/sessions/", json={"title": "Test"})
        assert response.status_code == 422


class TestReadSessions:
    def test_read_sessions_returns_empty_list_when_no_sessions_exist(self, client):
        response = client.get("/sessions/")
        assert response.status_code == 200
        assert response.json() == []

    def test_read_sessions_returns_list_of_all_available_sessions(self, client, created_session):
        response = client.get("/sessions/")
        assert response.status_code == 200
        sessions = response.json()
        assert len(sessions) == 1
        assert sessions[0]["title"] == created_session["title"]


class TestUpdateSession:
    def test_update_session_successfully_modifies_provided_session_fields(self, client, created_session):
        response = client.patch(f"/sessions/{created_session['id']}", json={
            "title": "Updated Rehearsal",
        })
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Rehearsal"

    def test_update_session_raises_404_when_session_id_is_nonexistent(self, client):
        response = client.patch("/sessions/9999", json={"title": "Test"})
        assert response.status_code == 404


class TestDeleteSession:
    def test_delete_session_removes_session_record_successfully(self, client, created_session):
        response = client.delete(f"/sessions/{created_session['id']}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

        # Verify it's gone
        response = client.get("/sessions/")
        assert len(response.json()) == 0

    def test_delete_session_raises_404_when_session_id_is_nonexistent(self, client):
        response = client.delete("/sessions/9999")
        assert response.status_code == 404

    def test_bulk_delete_sessions_removes_multiple_session_records_successfully(self, client):
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

    def test_bulk_delete_sessions_raises_400_when_ids_list_is_empty(self, client):
        response = client.post("/sessions/bulk-delete", json={"ids": []})
        assert response.status_code == 400
