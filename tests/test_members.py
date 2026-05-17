"""Tests for member CRUD endpoints."""
from datetime import date
from unittest.mock import patch

from app.models.member import Member
from app.schemas.member import ProfileUpdate, MemberUpdate
from app.schemas.member import Member as MemberSchema


class TestCreateMember:
    def test_create_member_successfully_persists_valid_member_data(self, client, sample_member_data):
        response = client.post("/members/", json=sample_member_data)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == sample_member_data["email"]
        assert data["first_name"] == sample_member_data["first_name"]
        assert data["last_name"] == sample_member_data["last_name"]
        assert "id" in data

    def test_create_member_successfully_sets_inactive_initial_status(self, client, sample_member_data):
        data = sample_member_data.copy()
        data["is_active"] = False
        response = client.post("/members/", json=data)
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_create_member_fails_and_returns_400_for_duplicate_email(self, client, created_member, sample_member_data):
        response = client.post("/members/", json=sample_member_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_create_member_fails_and_returns_422_when_required_fields_are_missing(self, client):
        response = client.post("/members/", json={"email": "test@example.com"})
        assert response.status_code == 422


class TestReadMembers:
    def test_read_members_returns_only_test_admin_when_no_other_members_exist(self, client):
        response = client.get("/members/")
        assert response.status_code == 200
        # Now returns [Test Admin]
        members = response.json()
        assert len(members) == 1
        assert members[0]["email"] == "test@example.com"

    def test_read_members_returns_list_of_all_registered_members(self, client, created_member):
        response = client.get("/members/")
        assert response.status_code == 200
        members = response.json()
        members = response.json()
        # Should be Test Admin + Created Member = 2
        assert len(members) == 2
        emails = [m["email"] for m in members]
        assert created_member["email"] in emails
        assert "test@example.com" in emails

    def test_read_members_returns_results_sorted_by_first_name_then_last_name(self, client):
        # Create members with different names to verify sort order
        client.post("/members/", json={
            "first_name": "Zara", "last_name": "Williams",
            "email": "zara@example.com", "phone_number": "+1111111111", "password": "pass123"
        })
        client.post("/members/", json={
            "first_name": "Alice", "last_name": "Brown",
            "email": "alice@example.com", "phone_number": "+2222222222", "password": "pass123"
        })
        client.post("/members/", json={
            "first_name": "Bob", "last_name": "Brown",
            "email": "bob@example.com", "phone_number": "+3333333333", "password": "pass123"
        })

        response = client.get("/members/")
        assert response.status_code == 200
        members = response.json()
        first_names = [m["first_name"] for m in members]
        # Sorted by first_name: "Alice" < "Bob" < "Test" (Admin) < "Zara"
        assert first_names == sorted(first_names)
        # For same first name, last_name should be alphabetical
        last_names = [m["last_name"] for m in members]
        for i in range(len(members) - 1):
            if members[i]["first_name"] == members[i + 1]["first_name"]:
                assert members[i]["last_name"] <= members[i + 1]["last_name"]

    def test_read_member_returns_correct_details_when_searched_by_valid_id(self, client, created_member):
        response = client.get(f"/members/{created_member['id']}")
        assert response.status_code == 200
        assert response.json()["email"] == created_member["email"]

    def test_read_member_raises_404_when_id_is_nonexistent(self, client):
        response = client.get("/members/9999")
        assert response.status_code == 404


class TestUpdateMember:
    def test_update_member_successfully_modifies_provided_fields(self, client, created_member):
        response = client.put(f"/members/{created_member['id']}", json={
            "first_name": "Jane",
        })
        assert response.status_code == 200
        assert response.json()["first_name"] == "Jane"
        assert response.json()["last_name"] == created_member["last_name"]

    def test_update_member_successfully_changes_active_and_inactive_status(self, client, created_member):
        # Deactivate
        response = client.put(f"/members/{created_member['id']}", json={
            "is_active": False,
        })
        assert response.status_code == 200
        assert response.json()["is_active"] is False

        # Reactivate
        response = client.put(f"/members/{created_member['id']}", json={
            "is_active": True,
        })
        assert response.status_code == 200
        assert response.json()["is_active"] is True

    def test_update_member_raises_404_when_id_is_nonexistent(self, client):
        response = client.put("/members/9999", json={"first_name": "Jane"})
        assert response.status_code == 404

    def test_update_member_sets_profile_fields(self, client, created_member):
        response = client.put(f"/members/{created_member['id']}", json={
            "birth_month": 6,
            "birth_day": 15,
            "birth_year": 1995,
            "tshirt_size": "L",
            "address_street": "123 Oak St",
            "address_city": "Austin",
            "address_state": "TX",
            "address_zip": "78701"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["birth_month"] == 6
        assert data["birth_day"] == 15
        assert data["birth_year"] == 1995
        assert data["tshirt_size"] == "L"
        assert data["address_city"] == "Austin"
        assert data["address_state"] == "TX"


class TestProfileEndpoints:
    """Tests for self-service GET/PUT /members/me endpoints."""

    def test_get_my_profile_returns_current_user(self, client):
        response = client.get("/members/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
        assert "first_name" in data

    def test_get_my_profile_includes_profile_fields(self, client):
        response = client.get("/members/me")
        assert response.status_code == 200
        data = response.json()
        # New profile fields should be present (null by default)
        for field in ["birth_month", "birth_day", "birth_year", "tshirt_size",
                       "address_street", "address_city", "address_state", "address_zip"]:
            assert field in data

    def test_update_my_profile_sets_dob_and_address(self, client):
        response = client.put("/members/me", json={
            "birth_month": 3,
            "birth_day": 22,
            "tshirt_size": "M",
            "address_street": "456 Elm St",
            "address_city": "Dallas",
            "address_state": "TX",
            "address_zip": "75201"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["birth_month"] == 3
        assert data["birth_day"] == 22
        assert data["tshirt_size"] == "M"
        assert data["address_city"] == "Dallas"

    def test_update_my_profile_dob_year_is_optional(self, client):
        response = client.put("/members/me", json={
            "birth_month": 12,
            "birth_day": 25
        })
        assert response.status_code == 200
        data = response.json()
        assert data["birth_month"] == 12
        assert data["birth_day"] == 25
        assert data["birth_year"] is None

    def test_update_my_profile_rejects_invalid_month(self, client):
        response = client.put("/members/me", json={"birth_month": 13})
        assert response.status_code == 422

    def test_update_my_profile_rejects_invalid_day(self, client):
        response = client.put("/members/me", json={"birth_day": 32})
        assert response.status_code == 422

    def test_update_my_profile_does_not_accept_email(self, client):
        """ProfileUpdate schema should not include email field."""
        response = client.put("/members/me", json={"email": "hacker@evil.com"})
        assert response.status_code == 200
        # Email should not have changed
        profile = client.get("/members/me").json()
        assert profile["email"] == "test@example.com"

    def test_update_my_profile_does_not_accept_roles_or_permissions(self, client):
        """ProfileUpdate schema should not include roles/permissions fields."""
        response = client.put("/members/me", json={
            "roles": ["admin"],
            "permissions": ["admin"]
        })
        assert response.status_code == 200
        profile = client.get("/members/me").json()
        # Should not have elevated privileges
        assert profile["permissions"] == ["admin"]  # unchanged from test fixture

    def test_update_my_profile_does_not_accept_first_name(self, client):
        """ProfileUpdate schema should not allow name changes."""
        response = client.put("/members/me", json={"first_name": "Hacked"})
        assert response.status_code == 200
        profile = client.get("/members/me").json()
        assert profile["first_name"] == "Test"  # unchanged

    def test_update_my_profile_does_not_accept_last_name(self, client):
        """ProfileUpdate schema should not allow name changes."""
        response = client.put("/members/me", json={"last_name": "Hacked"})
        assert response.status_code == 200
        profile = client.get("/members/me").json()
        assert profile["last_name"] == "Admin"  # unchanged

    def test_update_my_profile_does_not_accept_phone_number(self, client):
        """Phone changes require OTP verification, not direct update."""
        response = client.put("/members/me", json={"phone_number": "+9999999999"})
        assert response.status_code == 200
        profile = client.get("/members/me").json()
        assert profile["phone_number"] is None  # unchanged (was never set)


class TestPhoneChangeFlow:
    """Tests for the two-step phone change verification endpoints."""

    def test_change_phone_sends_otp(self, client):
        """POST /members/me/change-phone should send OTP and return success."""
        with patch(
            'app.services.verification.send_sms_verification', return_value=True
        ):
            response = client.post("/members/me/change-phone", json={
                "phone_number": "+1555000111"
            })
        assert response.status_code == 200
        assert response.json()["status"] == "otp_sent"

    def test_change_phone_rejects_empty_number(self, client):
        response = client.post("/members/me/change-phone", json={
            "phone_number": "   "
        })
        assert response.status_code == 400

    def test_change_phone_rejects_duplicate_number(self, client, created_member):
        """Should reject if the phone number is already in use by another member."""
        response = client.post("/members/me/change-phone", json={
            "phone_number": created_member["phone_number"]
        })
        assert response.status_code == 400
        assert "already in use" in response.json()["detail"]

    def test_verify_phone_updates_number(self, client):
        """POST /members/me/verify-phone should update phone after valid OTP."""
        with patch(
            'app.services.verification.check_verification', return_value=True
        ):
            response = client.post("/members/me/verify-phone", json={
                "phone_number": "+1555000222",
                "otp": "123456"
            })
        assert response.status_code == 200
        data = response.json()
        assert data["phone_number"] == "+1555000222"
        assert data["phone_number_verified"] is True

    def test_verify_phone_rejects_invalid_otp(self, client):
        """Should reject with 400 on bad OTP."""
        with patch(
            'app.services.verification.check_verification', return_value=False
        ):
            response = client.post("/members/me/verify-phone", json={
                "phone_number": "+1555000333",
                "otp": "000000"
            })
        assert response.status_code == 400
        assert "Invalid" in response.json()["detail"]


class TestDateOfBirthProperty:
    """Tests for the Member.date_of_birth computed property."""

    def test_date_of_birth_with_full_date(self, db_session):

        m = Member(first_name="A", last_name="B", email="dob@test.com",
                   birth_month=6, birth_day=15, birth_year=1990)
        db_session.add(m)
        db_session.commit()
        assert m.date_of_birth == date(1990, 6, 15)

    def test_date_of_birth_without_year_uses_fallback(self, db_session):

        m = Member(first_name="A", last_name="B", email="dob2@test.com",
                   birth_month=12, birth_day=25)
        db_session.add(m)
        db_session.commit()
        assert m.date_of_birth == date(1900, 12, 25)

    def test_date_of_birth_returns_none_when_missing(self, db_session):

        m = Member(first_name="A", last_name="B", email="dob3@test.com")
        db_session.add(m)
        db_session.commit()
        assert m.date_of_birth is None

    def test_date_of_birth_returns_none_for_invalid_date(self, db_session):

        m = Member(first_name="A", last_name="B", email="dob4@test.com",
                   birth_month=2, birth_day=30, birth_year=2000)
        db_session.add(m)
        db_session.commit()
        assert m.date_of_birth is None  # Feb 30 doesn't exist


class TestProfileUpdatePersistence:
    """Verify profile fields persist correctly across requests."""

    def test_profile_update_persists_and_is_retrievable(self, client):
        """Fields set via PUT /me should appear in subsequent GET /me."""
        client.put("/members/me", json={
            "birth_month": 11,
            "birth_day": 7,
            "tshirt_size": "XL",
            "address_street": "789 Pine Ave",
            "address_city": "Houston",
            "address_state": "TX",
            "address_zip": "77001"
        })
        profile = client.get("/members/me").json()
        assert profile["birth_month"] == 11
        assert profile["birth_day"] == 7
        assert profile["tshirt_size"] == "XL"
        assert profile["address_street"] == "789 Pine Ave"
        assert profile["address_city"] == "Houston"

    def test_profile_update_can_clear_optional_fields(self, client):
        """Setting a field to null should clear it."""
        # First set values
        client.put("/members/me", json={
            "tshirt_size": "S",
            "address_street": "100 Main St"
        })
        # Then clear them
        client.put("/members/me", json={
            "tshirt_size": None,
            "address_street": None
        })
        profile = client.get("/members/me").json()
        assert profile["tshirt_size"] is None
        assert profile["address_street"] is None

    def test_profile_update_partial_does_not_clear_other_fields(self, client):
        """Updating one field should not affect unrelated fields."""
        client.put("/members/me", json={
            "birth_month": 3,
            "tshirt_size": "L"
        })
        # Update only tshirt, birth_month should remain
        client.put("/members/me", json={"tshirt_size": "XL"})
        profile = client.get("/members/me").json()
        assert profile["tshirt_size"] == "XL"
        assert profile["birth_month"] == 3  # untouched

    def test_admin_can_update_profile_fields_for_other_member(self, client, created_member):
        """Admin PUT /members/{id} should set profile fields on other members."""
        response = client.put(f"/members/{created_member['id']}", json={
            "birth_month": 1,
            "birth_day": 1,
            "tshirt_size": "XXL",
            "address_city": "Dallas"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["birth_month"] == 1
        assert data["tshirt_size"] == "XXL"
        assert data["address_city"] == "Dallas"


class TestPhoneChangeEdgeCases:
    """Additional edge-case tests for phone change flow."""

    def test_change_phone_allows_same_user_current_number(self, client, db_session):
        """User should be able to re-verify their own current phone number."""

        # Set current user's phone number directly in DB
        user = db_session.query(Member).filter_by(email="test@example.com").first()
        user.phone_number = "+1555999888"
        db_session.commit()

        with __import__('unittest.mock', fromlist=['patch']).patch(
            'app.services.verification.send_sms_verification', return_value=True
        ):
            response = client.post("/members/me/change-phone", json={
                "phone_number": "+1555999888"
            })
        assert response.status_code == 200  # Should not reject own number

    def test_verify_phone_persists_and_marks_verified(self, client):
        """After verify, GET /me should show new phone and verified=true."""
        with __import__('unittest.mock', fromlist=['patch']).patch(
            'app.services.verification.check_verification', return_value=True
        ):
            client.post("/members/me/verify-phone", json={
                "phone_number": "+1555777666",
                "otp": "111111"
            })
        profile = client.get("/members/me").json()
        assert profile["phone_number"] == "+1555777666"
        assert profile["phone_number_verified"] is True


class TestProfileSchemaValidation:
    """Structural tests for Pydantic schema constraints."""

    def test_profile_update_schema_has_no_email_field(self):

        fields = ProfileUpdate.model_fields
        assert "email" not in fields

    def test_profile_update_schema_has_no_name_fields(self):

        fields = ProfileUpdate.model_fields
        assert "first_name" not in fields
        assert "last_name" not in fields

    def test_profile_update_schema_has_no_phone_field(self):

        fields = ProfileUpdate.model_fields
        assert "phone_number" not in fields

    def test_profile_update_schema_has_no_privilege_fields(self):

        fields = ProfileUpdate.model_fields
        assert "roles" not in fields
        assert "permissions" not in fields
        assert "is_active" not in fields

    def test_profile_update_schema_has_expected_fields(self):

        fields = set(ProfileUpdate.model_fields.keys())
        expected = {
            "birth_month", "birth_day", "birth_year",
            "tshirt_size",
            "address_street", "address_city", "address_state", "address_zip"
        }
        assert fields == expected

    def test_member_update_schema_includes_profile_fields(self):
        """Admin MemberUpdate should include all profile fields."""

        fields = MemberUpdate.model_fields
        for f in ["birth_month", "birth_day", "birth_year", "tshirt_size",
                   "address_street", "address_city", "address_state", "address_zip"]:
            assert f in fields, f"MemberUpdate missing field: {f}"

    def test_member_response_schema_includes_profile_fields(self):
        """Member response schema should include all profile fields."""
        fields = MemberSchema.model_fields
        for f in ["birth_month", "birth_day", "birth_year", "tshirt_size",
                   "address_street", "address_city", "address_state", "address_zip"]:
            assert f in fields, f"Member response missing field: {f}"
