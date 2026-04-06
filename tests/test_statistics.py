"""
Tests for statistics endpoints.
Covers: /statistics/member/{member_id}
"""


class TestMemberStats:
    def test_member_stats_not_found(self, client):
        response = client.get("/statistics/member/9999")
        assert response.status_code == 404

    def test_member_stats_no_attendance(self, client, created_member):
        response = client.get(f"/statistics/member/{created_member['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["member_name"] == created_member["full_name"]
        assert data["history"] == []

    def test_member_stats_with_attendance(self, client, created_member, created_session):
        # Mark attendance (timestamp will be after start_time, so "late")
        client.post("/attendance/", json={
            "member_id": created_member["id"],
            "session_id": created_session["id"],
            "latitude": None,
            "longitude": None,
            "submission_type": "manual",
            "marked_by_id": None,
        })

        response = client.get(f"/statistics/member/{created_member['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["member_name"] == created_member["full_name"]
        assert len(data["history"]) == 1
        assert data["history"][0]["session_title"] == created_session["title"]
        assert data["history"][0]["status"] in ("prompt", "late")
