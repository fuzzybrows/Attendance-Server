"""
Tests for QR attendance endpoints.
Covers: /attendance/qr/token/{session_id} and /attendance/qr/mark
"""
from app.core.auth import create_access_token


class TestQRToken:
    def test_generate_qr_token_succeeds_and_returns_token_with_valid_expiry(self, client, created_session):
        response = client.get(f"/attendance/qr/token/{created_session['id']}")
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["expires_in"] == 30

    def test_generate_qr_token_fails_and_returns_404_when_session_is_nonexistent(self, client):
        response = client.get("/attendance/qr/token/9999")
        assert response.status_code == 404


class TestQRMark:
    def test_mark_qr_attendance_succeeds_successfully_updates_member_attendance_status(self, client, created_member, created_session):
        # Generate QR token
        qr_resp = client.get(f"/attendance/qr/token/{created_session['id']}")
        qr_token = qr_resp.json()["token"]

        # Generate auth token with member email as sub
        auth_token = create_access_token(data={"sub": created_member["email"]})

        response = client.post(
            "/attendance/qr/mark",
            params={"session_id": created_session["id"], "qr_token": qr_token},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "attendance_id" in data
        assert data["member_name"] == created_member["full_name"]

    def test_mark_qr_attendance_fails_and_returns_401_when_token_is_expired_or_invalid(self, client, created_member, created_session):
        auth_token = create_access_token(data={"sub": created_member["email"]})
        response = client.post(
            "/attendance/qr/mark",
            params={"session_id": created_session["id"], "qr_token": "bad.token.here"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower() or "QR" in response.json()["detail"]

    def test_mark_qr_attendance_fails_and_returns_401_when_auth_token_is_invalid(self, client, created_session):
        qr_resp = client.get(f"/attendance/qr/token/{created_session['id']}")
        qr_token = qr_resp.json()["token"]

        response = client.post(
            "/attendance/qr/mark",
            params={"session_id": created_session["id"], "qr_token": qr_token},
            headers={"Authorization": "Bearer invalid.auth.token"},
        )
        assert response.status_code == 401

    def test_mark_qr_attendance_fails_and_returns_400_when_session_id_mismatches_token(self, client, created_member, created_session):
        # Generate QR for one session, try to mark for another
        qr_resp = client.get(f"/attendance/qr/token/{created_session['id']}")
        qr_token = qr_resp.json()["token"]
        auth_token = create_access_token(data={"sub": created_member["email"]})

        response = client.post(
            "/attendance/qr/mark",
            params={"session_id": 9999, "qr_token": qr_token},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 400
        assert "does not match" in response.json()["detail"]

    def test_mark_qr_attendance_fails_and_returns_409_on_duplicate_marking_attempt(self, client, created_member, created_session):
        qr_resp = client.get(f"/attendance/qr/token/{created_session['id']}")
        qr_token = qr_resp.json()["token"]
        auth_token = create_access_token(data={"sub": created_member["email"]})

        # First mark
        client.post(
            "/attendance/qr/mark",
            params={"session_id": created_session["id"], "qr_token": qr_token},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        # Get a fresh QR token for second attempt
        qr_resp2 = client.get(f"/attendance/qr/token/{created_session['id']}")
        qr_token2 = qr_resp2.json()["token"]

        response = client.post(
            "/attendance/qr/mark",
            params={"session_id": created_session["id"], "qr_token": qr_token2},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 409

    def test_mark_qr_attendance_fails_and_returns_422_when_auth_header_is_missing(self, client, created_session):
        qr_resp = client.get(f"/attendance/qr/token/{created_session['id']}")
        qr_token = qr_resp.json()["token"]

        response = client.post(
            "/attendance/qr/mark",
            params={"session_id": created_session["id"], "qr_token": qr_token},
        )
        assert response.status_code == 422  # Missing required header

    def test_mark_qr_attendance_fails_and_returns_400_when_provided_token_is_not_qr_type(self, client, created_member, created_session):
        auth_token = create_access_token(data={"sub": created_member["email"]})

        response = client.post(
            "/attendance/qr/mark",
            params={"session_id": created_session["id"], "qr_token": auth_token},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 400
        assert "Invalid QR token type" in response.json()["detail"]
