"""Tests for member CRUD endpoints."""


class TestCreateMember:
    def test_create_member(self, client, sample_member_data):
        """Test creating a new member."""
        response = client.post("/members/", json=sample_member_data)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == sample_member_data["email"]
        assert data["first_name"] == sample_member_data["first_name"]
        assert data["last_name"] == sample_member_data["last_name"]
        assert "id" in data

    def test_create_member_duplicate_email(self, client, created_member, sample_member_data):
        """Test creating a member with duplicate email fails."""
        response = client.post("/members/", json=sample_member_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_create_member_missing_fields(self, client):
        """Test creating a member with missing required fields."""
        response = client.post("/members/", json={"email": "test@example.com"})
        assert response.status_code == 422


class TestReadMembers:
    def test_read_members_empty(self, client):
        """Test reading members when none exist."""
        response = client.get("/members/")
        assert response.status_code == 200
        # Now returns [Test Admin]
        members = response.json()
        assert len(members) == 1
        assert members[0]["email"] == "test@example.com"

    def test_read_members(self, client, created_member):
        """Test reading all members."""
        response = client.get("/members/")
        assert response.status_code == 200
        members = response.json()
        members = response.json()
        # Should be Test Admin + Created Member = 2
        assert len(members) == 2
        emails = [m["email"] for m in members]
        assert created_member["email"] in emails
        assert "test@example.com" in emails

    def test_read_member_by_id(self, client, created_member):
        """Test reading a single member by ID."""
        response = client.get(f"/members/{created_member['id']}")
        assert response.status_code == 200
        assert response.json()["email"] == created_member["email"]

    def test_read_member_not_found(self, client):
        """Test reading a non-existent member."""
        response = client.get("/members/9999")
        assert response.status_code == 404


class TestUpdateMember:
    def test_update_member(self, client, created_member):
        """Test updating a member's details."""
        response = client.put(f"/members/{created_member['id']}", json={
            "first_name": "Jane",
        })
        assert response.status_code == 200
        assert response.json()["first_name"] == "Jane"
        assert response.json()["last_name"] == created_member["last_name"]

    def test_update_member_not_found(self, client):
        """Test updating a non-existent member."""
        response = client.put("/members/9999", json={"first_name": "Jane"})
        assert response.status_code == 404
