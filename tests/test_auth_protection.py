"""
Tests that protected endpoints return 401 without authentication.
Uses the unauth_client fixture (no get_current_user override).
"""


class TestUnauthenticatedAccess:
    """Verify all protected endpoints reject unauthenticated requests."""

    def test_members_list_requires_auth(self, unauth_client):
        response = unauth_client.get("/members/")
        assert response.status_code == 401

    def test_sessions_list_requires_auth(self, unauth_client):
        response = unauth_client.get("/sessions/")
        assert response.status_code == 401

    def test_attendance_stats_requires_auth(self, unauth_client):
        response = unauth_client.get("/attendance/stats")
        assert response.status_code == 401

    def test_statistics_requires_auth(self, unauth_client):
        response = unauth_client.get("/statistics/member/1")
        assert response.status_code == 401

    def test_auth_login_is_public(self, unauth_client):
        """Auth endpoints should remain accessible without a token."""
        response = unauth_client.post("/auth/login", json={"login": "x", "password": "y"})
        # 401 from bad creds, but NOT from missing token
        assert response.status_code != 401 or "Invalid or expired token" not in response.text
