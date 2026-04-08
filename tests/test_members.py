"""Tests for member CRUD endpoints."""


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
