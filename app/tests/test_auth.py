"""Tests for auth endpoints: login, OTP verification, password reset."""
from unittest.mock import patch


class TestLogin:
    def test_login_success(self, client, created_member, sample_member_data):
        """Test successful login with valid credentials."""
        response = client.post("/auth/login", json={
            "login": sample_member_data["email"],
            "password": sample_member_data["password"],
        })
        assert response.status_code == 200
        data = response.json()
        # Unverified user should get verification prompt
        assert data["status"] == "unverified"
        assert data["method"] == "email"

    def test_login_invalid_credentials(self, client, created_member):
        """Test login with wrong password."""
        response = client.post("/auth/login", json={
            "login": "john@example.com",
            "password": "wrongpassword",
        })
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post("/auth/login", json={
            "login": "nobody@example.com",
            "password": "password",
        })
        assert response.status_code == 401

    def test_login_verified_user_gets_token(self, client, db_session, created_member, sample_member_data):
        """Test that a verified user gets an access token."""
        import models
        member = db_session.query(models.Member).filter_by(email=sample_member_data["email"]).first()
        member.email_verified = True
        db_session.commit()

        response = client.post("/auth/login", json={
            "login": sample_member_data["email"],
            "password": sample_member_data["password"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["member"]["email"] == sample_member_data["email"]


class TestVerifyOTP:
    def test_verify_otp_success(self, client, created_member, sample_member_data):
        """Test successful OTP verification (uses placeholder Twilio)."""
        response = client.post("/auth/verify-otp", json={
            "login": sample_member_data["email"],
            "otp": "123456",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["member"]["email"] == sample_member_data["email"]

    def test_verify_otp_invalid(self, client, created_member, sample_member_data):
        """Test OTP verification with invalid code."""
        response = client.post("/auth/verify-otp", json={
            "login": sample_member_data["email"],
            "otp": "abc",  # Not 6 digits
        })
        assert response.status_code == 400


class TestPasswordReset:
    def test_forgot_password_sends_otp(self, client, created_member, sample_member_data):
        """Test forgot password initiates OTP."""
        response = client.post(
            "/auth/forgot-password",
            params={"login": sample_member_data["email"]}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "otp_sent"

    def test_forgot_password_unknown_user(self, client):
        """Test forgot password for non-existent user."""
        response = client.post(
            "/auth/forgot-password",
            params={"login": "nobody@example.com"}
        )
        assert response.status_code == 404

    def test_reset_password_marks_verified(self, client, db_session, created_member, sample_member_data):
        """Test that password reset marks the user as verified."""
        import models
        response = client.post(
            "/auth/reset-password",
            json={"login": sample_member_data["email"], "otp": "123456"},
            params={"new_password": "newpassword123"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "password_reset_success"

        # Verify the member is now marked as verified
        db_session.expire_all()
        member = db_session.query(models.Member).filter_by(email=sample_member_data["email"]).first()
        assert member.email_verified is True


class TestPhoneAuth:
    """Tests for phone-number-based auth paths (covers SMS branches)."""

    def test_login_unverified_phone_sends_sms(self, client, db_session, sample_member_data):
        """Login via phone number with unverified phone sends SMS OTP."""
        import models
        from auth import get_password_hash
        # Create member with phone number
        db_session.add(models.Member(
            first_name="Phone", last_name="User",
            email="phone_user@test.com",
            phone_number="+15551234567",
            password_hash=get_password_hash("pass123"),
        ))
        db_session.commit()

        response = client.post("/auth/login", json={
            "login": "+15551234567",
            "password": "pass123",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unverified"
        assert data["method"] == "phone"

    def test_verify_otp_by_phone(self, client, db_session):
        """OTP verification via phone marks phone_number_verified."""
        import models
        from auth import get_password_hash
        db_session.add(models.Member(
            first_name="Phone", last_name="OTP",
            email="phone_otp@test.com",
            phone_number="+15559876543",
            password_hash=get_password_hash("pass123"),
        ))
        db_session.commit()

        response = client.post("/auth/verify-otp", json={
            "login": "+15559876543",
            "otp": "123456",
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

        db_session.expire_all()
        member = db_session.query(models.Member).filter_by(phone_number="+15559876543").first()
        assert member.phone_number_verified is True

    def test_forgot_password_by_phone(self, client, db_session):
        """Forgot password via phone number sends SMS OTP."""
        import models
        from auth import get_password_hash
        db_session.add(models.Member(
            first_name="Phone", last_name="Reset",
            email="phone_reset@test.com",
            phone_number="+15550001111",
            password_hash=get_password_hash("pass123"),
        ))
        db_session.commit()

        response = client.post(
            "/auth/forgot-password",
            params={"login": "+15550001111"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "otp_sent"

    def test_reset_password_by_phone(self, client, db_session):
        """Password reset via phone marks phone_number_verified."""
        import models
        from auth import get_password_hash
        db_session.add(models.Member(
            first_name="Phone", last_name="ResetPw",
            email="phone_resetpw@test.com",
            phone_number="+15550002222",
            password_hash=get_password_hash("pass123"),
        ))
        db_session.commit()

        response = client.post(
            "/auth/reset-password",
            json={"login": "+15550002222", "otp": "123456"},
            params={"new_password": "newpass456"},
        )
        assert response.status_code == 200

        db_session.expire_all()
        member = db_session.query(models.Member).filter_by(phone_number="+15550002222").first()
        assert member.phone_number_verified is True

