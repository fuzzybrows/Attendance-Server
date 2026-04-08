"""Tests for auth endpoints: login, OTP verification, password reset."""
from unittest.mock import patch
from app.models.member import Member
from app.core.auth import get_password_hash


class TestLogin:
    def test_login_succeeds_with_valid_credentials_and_returns_unverified_status(self, client, created_member, sample_member_data):
        response = client.post("/auth/login", json={
            "login": sample_member_data["email"],
            "password": sample_member_data["password"],
            "recaptcha_token": "test-token"
        })
        assert response.status_code == 200
        data = response.json()
        # Unverified user should get verification prompt
        assert data["status"] == "unverified"
        assert data["method"] == "email"

    def test_login_fails_and_returns_401_with_wrong_password(self, client, created_member):
        response = client.post("/auth/login", json={
            "login": "john@example.com",
            "password": "wrongpassword",
            "recaptcha_token": "test-token"
        })
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials or account disabled"

    def test_login_fails_and_returns_401_for_disabled_account(self, client, db_session, created_member, sample_member_data):
        member = db_session.query(Member).filter_by(email=sample_member_data["email"]).first()
        member.is_active = False
        db_session.commit()

        response = client.post("/auth/login", json={
            "login": sample_member_data["email"],
            "password": sample_member_data["password"],
            "recaptcha_token": "test-token"
        })
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials or account disabled"

    def test_login_fails_and_returns_401_for_nonexistent_user(self, client):
        response = client.post("/auth/login", json={
            "login": "nobody@example.com",
            "password": "password",
            "recaptcha_token": "test-token"
        })
        assert response.status_code == 401

    def test_login_succeeds_and_returns_token_for_verified_user(self, client, db_session, created_member, sample_member_data):
        member = db_session.query(Member).filter_by(email=sample_member_data["email"]).first()
        member.email_verified = True
        db_session.commit()

        response = client.post("/auth/login", json={
            "login": sample_member_data["email"],
            "password": sample_member_data["password"],
            "recaptcha_token": "test-token"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["member"]["email"] == sample_member_data["email"]


class TestVerifyOTP:
    def test_verify_otp_succeeds_with_valid_code_and_returns_token(self, client, created_member, sample_member_data):
        response = client.post("/auth/verify-otp", json={
            "login": sample_member_data["email"],
            "otp": "123456",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["member"]["email"] == sample_member_data["email"]

    def test_verify_otp_fails_and_returns_400_with_invalid_code_format(self, client, created_member, sample_member_data):
        response = client.post("/auth/verify-otp", json={
            "login": sample_member_data["email"],
            "otp": "abc",  # Not 6 digits
        })
        assert response.status_code == 400


class TestPasswordReset:
    def test_forgot_password_successfully_initiates_otp_delivery(self, client, created_member, sample_member_data):
        response = client.post(
            "/auth/forgot-password",
            json={"login": sample_member_data["email"], "recaptcha_token": "test-token"}
        )
        assert response.status_code == 200
        assert "account matching" in response.json()["status"]

    def test_forgot_password_returns_generic_success_even_for_unknown_user(self, client):
        response = client.post(
            "/auth/forgot-password",
            json={"login": "nobody@example.com", "recaptcha_token": "test-token"}
        )
        assert response.status_code == 200
        assert "account matching" in response.json()["status"]

    def test_reset_password_succeeds_and_marks_member_as_verified(self, client, db_session, created_member, sample_member_data):
        response = client.post(
            "/auth/reset-password",
            json={
                "login": sample_member_data["email"],
                "otp": "123456",
                "new_password": "NewPassword123!"
            }
        )
        assert response.status_code == 200
        assert response.json()["status"] == "password_reset_success"

        # Verify the member is now marked as verified
        db_session.expire_all()
        member = db_session.query(Member).filter_by(email=sample_member_data["email"]).first()
        assert member.email_verified is True


class TestPhoneAuth:
    """Tests for phone-number-based auth paths (covers SMS branches)."""

    def test_login_with_unverified_phone_number_triggers_sms_otp_delivery(self, client, db_session, sample_member_data):
        # Create member with phone number
        db_session.add(Member(
            first_name="Phone", last_name="User",
            email="phone_user@test.com",
            phone_number="+15551234567",
            password_hash=get_password_hash("pass123"),
        ))
        db_session.commit()

        response = client.post("/auth/login", json={
            "login": "+15551234567",
            "password": "pass123",
            "recaptcha_token": "test-token"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unverified"
        assert data["method"] == "phone"

    def test_verify_otp_via_phone_number_successfully_marks_phone_as_verified(self, client, db_session):
        db_session.add(Member(
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
        member = db_session.query(Member).filter_by(phone_number="+15559876543").first()
        assert member.phone_number_verified is True

    def test_forgot_password_request_via_phone_number_triggers_sms_otp(self, client, db_session):
        db_session.add(Member(
            first_name="Phone", last_name="Reset",
            email="phone_reset@test.com",
            phone_number="+15550001111",
            password_hash=get_password_hash("pass123"),
        ))
        db_session.commit()

        response = client.post(
            "/auth/forgot-password",
            json={"login": "+15550001111", "recaptcha_token": "test-token"}
        )
        assert response.status_code == 200
        assert "account matching" in response.json()["status"]

    def test_reset_password_via_phone_number_successfully_marks_phone_as_verified(self, client, db_session):
        db_session.add(Member(
            first_name="Phone", last_name="ResetPw",
            email="phone_resetpw@test.com",
            phone_number="+15550002222",
            password_hash=get_password_hash("pass123"),
        ))
        db_session.commit()

        response = client.post(
            "/auth/reset-password",
            json={
                "login": "+15550002222",
                "otp": "123456",
                "new_password": "NewPass456!"
            },
        )
        assert response.status_code == 200

        db_session.expire_all()
        member = db_session.query(Member).filter_by(phone_number="+15550002222").first()
        assert member.phone_number_verified is True

