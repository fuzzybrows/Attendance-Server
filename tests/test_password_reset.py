"""Tests for password reset functionality."""
import pytest
from unittest.mock import patch
from app.core.auth import verify_password
from app.models.member import Member

class TestPasswordReset:
    def test_admin_reset_member_password_updates_db(self, client, db_session, created_member):
        """Test that an admin resetting a member's password correctly updates the database."""
        new_password = "NewSecurePassword123!"
        member_id = created_member["id"]
        
        # Initial check
        member_before = db_session.get(Member, member_id)
        old_hash = member_before.password_hash
        
        # Reset password
        response = client.post(
            f"/members/{member_id}/reset-password",
            json={"new_password": new_password}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
        # Verify DB update
        db_session.expire_all()
        member_after = db_session.get(Member, member_id)
        assert member_after.password_hash != old_hash
        assert verify_password(new_password, member_after.password_hash)

    @patch("app.routers.auth.check_verification")
    def test_public_reset_password_updates_db(self, mock_check, unauth_client, db_session, created_member):
        """Test that the public OTP-based password reset correctly updates the database and expects a body."""
        mock_check.return_value = True
        new_password = "AnotherNewPassword123!"
        login = created_member["email"]
        
        # 1. Verify it fails with query parameters now (validation error 422 because body is missing)
        response_query = unauth_client.post(
            f"/auth/reset-password?new_password={new_password}",
            json={"login": login, "otp": "123456"}
        )
        assert response_query.status_code == 422
        
        # 2. Verify it succeeds with body-based request
        response = unauth_client.post(
            "/auth/reset-password",
            json={
                "login": login,
                "otp": "123456",
                "new_password": new_password
            }
        )
        assert response.status_code == 200
        assert response.json()["status"] == "password_reset_success"
        
        # 3. Verify DB update
        db_session.expire_all()
        member = db_session.query(Member).filter_by(email=login).first()
        assert verify_password(new_password, member.password_hash)
        
        # 4. Verify login with new password works
        login_response = unauth_client.post(
            "/auth/login",
            json={
                "login": login,
                "password": new_password
            }
        )
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()

    @patch("app.routers.auth.check_verification")
    def test_public_reset_password_invalid_otp(self, mock_check, unauth_client, created_member):
        """Test that an invalid OTP prevents password reset."""
        mock_check.return_value = False
        
        response = unauth_client.post(
            "/auth/reset-password",
            json={
                "login": created_member["email"],
                "otp": "wrong-otp",
                "new_password": "NewPassword123!"
            }
        )
        assert response.status_code == 400
        assert "Invalid or expired OTP" in response.json()["detail"]
