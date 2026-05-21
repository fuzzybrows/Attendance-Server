"""
Tests for the role genericization changes:
  - sunday_qualifier_id / sunday_qualifier_role on Role model
  - /members/metadata returns sunday_qualifiers + feature flags
  - generate_schedule: Sunday pool filter is DB-driven and flag-gated
  - generate_schedule: raises 422 when no assignable roles are configured
  - CSV export: columns built from assignable roles dynamically
  - PDF export: columns built from assignable roles dynamically
"""
import pytest
from datetime import datetime
from unittest.mock import patch

from app.models.member import Member, Role
from app.models.session import Session as SessionModel
from app.models.assignment import Assignment
from app.settings import settings


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_role(db, name, display_order=None, sunday_qualifier=None):
    """Create or fetch a role. Optionally set display_order and sunday_qualifier_role."""
    role = db.query(Role).filter_by(name=name).first()
    if not role:
        role = Role(name=name, display_order=display_order)
        db.add(role)
        db.flush()
    if sunday_qualifier is not None:
        role.sunday_qualifier_role = sunday_qualifier
    db.commit()
    return role


def make_member(db, first, last, email, roles, is_active=True):
    m = Member(first_name=first, last_name=last, email=email,
               password_hash="hash", is_active=is_active, roles=roles)
    db.add(m)
    db.commit()
    return m


def make_program_session(db, title, dt, month=None):
    """Create a program session. dt is a datetime object."""
    s = SessionModel(title=title, type="program",
                     start_time=dt,
                     end_time=dt.replace(hour=dt.hour + 2),
                     status="scheduled")
    db.add(s)
    db.commit()
    return s


# ── Role Model Tests ───────────────────────────────────────────────────────────

class TestRoleSundayQualifier:
    """Verify the self-referential sunday_qualifier_id FK on the Role model."""

    def test_role_sunday_qualifier_defaults_to_none(self, db_session):
        role = make_role(db_session, "test_lead_singer", display_order=1)
        assert role.sunday_qualifier_id is None
        assert role.sunday_qualifier_role is None

    def test_role_sunday_qualifier_can_be_set_to_another_role(self, db_session):
        qualifier = make_role(db_session, "sunday_qualifier_test_role")
        lead = make_role(db_session, "test_lead_q", display_order=1, sunday_qualifier=qualifier)
        db_session.refresh(lead)
        assert lead.sunday_qualifier_id == qualifier.id
        assert lead.sunday_qualifier_role.name == qualifier.name

    def test_role_sunday_qualifier_is_assignable_is_independent(self, db_session):
        """sunday_qualifier_role should have no display_order (not itself schedulable)."""
        qualifier = make_role(db_session, "sunday_q2_role", display_order=None)
        lead = make_role(db_session, "test_lead_q2", display_order=1, sunday_qualifier=qualifier)
        assert lead.is_assignable is True
        assert qualifier.is_assignable is False


# ── /members/metadata Tests ────────────────────────────────────────────────────

class TestMemberMetadataEndpoint:
    """Verify /members/metadata now returns sunday_qualifiers + feature flags."""

    def test_metadata_returns_sunday_qualifiers_map(self, client, db_session):
        qualifier = make_role(db_session, "sunday_qualifier_metadata_role")
        lead = make_role(db_session, "metadata_lead", display_order=1, sunday_qualifier=qualifier)
        db_session.refresh(lead)

        response = client.get("/members/metadata")
        assert response.status_code == 200
        data = response.json()
        assert "sunday_qualifiers" in data
        assert data["sunday_qualifiers"].get("metadata_lead") == qualifier.name

    def test_metadata_returns_empty_qualifiers_when_none_set(self, client, db_session):
        make_role(db_session, "no_qualifier_role", display_order=2)
        response = client.get("/members/metadata")
        assert response.status_code == 200
        data = response.json()
        assert "sunday_qualifiers" in data
        # "no_qualifier_role" should not appear in qualifiers
        assert "no_qualifier_role" not in data["sunday_qualifiers"]

    def test_metadata_returns_enable_sunday_pool_filter_flag(self, client):
        response = client.get("/members/metadata")
        assert response.status_code == 200
        data = response.json()
        assert "enable_sunday_pool_filter" in data
        assert isinstance(data["enable_sunday_pool_filter"], bool)

    def test_metadata_returns_enable_sunday_preview_defaults_flag(self, client):
        response = client.get("/members/metadata")
        assert response.status_code == 200
        data = response.json()
        assert "enable_sunday_preview_defaults" in data
        assert isinstance(data["enable_sunday_preview_defaults"], bool)

    def test_metadata_sunday_qualifiers_only_includes_assignable_roles(self, client, db_session):
        """Non-assignable roles should not appear in sunday_qualifiers, even if they
        happen to have a sunday_qualifier_role set."""
        qualifier = make_role(db_session, "q_role_non_assign")
        non_assignable = make_role(db_session, "non_assign_role", display_order=None,
                                    sunday_qualifier=qualifier)
        response = client.get("/members/metadata")
        data = response.json()
        assert "non_assign_role" not in data["sunday_qualifiers"]


# ── generate_schedule: Sunday Pool Filter Tests ───────────────────────────────

class TestGenerateScheduleSundayQualifier:
    """
    Verify that the Sunday pool filter is:
      1. DB-driven (reads role.sunday_qualifier_role, no hardcoded name)
      2. Flag-gated (ENABLE_SUNDAY_POOL_FILTER=false disables it)
      3. Ignored on non-Sunday sessions even when flag is on
      4. Ignored for roles that have no sunday_qualifier_role
    """

    def _setup_sunday_session(self, db_session):
        """Sunday April 12 2026."""
        return make_program_session(db_session, "Sunday Service",
                                    datetime(2026, 4, 12, 10, 0))

    def _setup_weekday_session(self, db_session):
        """Wednesday April 15 2026."""
        return make_program_session(db_session, "Wednesday Service",
                                    datetime(2026, 4, 15, 10, 0))

    def test_sunday_pool_filter_on_restricts_to_qualifier_holders(
            self, client, db_session):
        qualifier = make_role(db_session, "sunday_lead_qualifier_a")
        lead = make_role(db_session, "lead_q_a", display_order=1, sunday_qualifier=qualifier)

        regular = make_member(db_session, "Regular", "A", "regular_a@test.com", [lead])
        qualified = make_member(db_session, "Qualified", "A", "qualified_a@test.com",
                                [lead, qualifier])
        self._setup_sunday_session(db_session)

        with patch.object(settings, 'enable_sunday_pool_filter', True):
            response = client.post("/calendar/schedule/generate",
                                   json={"year": 2026, "month": 4})
        assert response.status_code == 200

        assigned_ids = {a["member_id"] for s in response.json()["sessions"]
                        for a in s["assignments"]}
        assert qualified.id in assigned_ids
        assert regular.id not in assigned_ids

    def test_sunday_pool_filter_off_allows_all_members_on_sunday(
            self, client, db_session):
        qualifier = make_role(db_session, "sunday_lead_qualifier_b")
        lead = make_role(db_session, "lead_q_b", display_order=1, sunday_qualifier=qualifier)

        regular = make_member(db_session, "Regular", "B", "regular_b@test.com", [lead])
        qualified = make_member(db_session, "Qualified", "B", "qualified_b@test.com",
                                [lead, qualifier])
        self._setup_sunday_session(db_session)

        with patch.object(settings, 'enable_sunday_pool_filter', False):
            response = client.post("/calendar/schedule/generate",
                                   json={"year": 2026, "month": 4})
        assert response.status_code == 200

        assigned_ids = {a["member_id"] for s in response.json()["sessions"]
                        for a in s["assignments"]}
        # With flag off, both are in the pool; exactly one gets assigned
        assert qualified.id in assigned_ids or regular.id in assigned_ids

    def test_sunday_pool_filter_does_not_apply_on_weekday_sessions(
            self, client, db_session):
        qualifier = make_role(db_session, "sunday_lead_qualifier_c")
        lead = make_role(db_session, "lead_q_c", display_order=1, sunday_qualifier=qualifier)

        # Only has the base role — no qualifier
        regular = make_member(db_session, "Regular", "C", "regular_c@test.com", [lead])
        self._setup_weekday_session(db_session)

        with patch.object(settings, 'enable_sunday_pool_filter', True):
            response = client.post("/calendar/schedule/generate",
                                   json={"year": 2026, "month": 4})
        assert response.status_code == 200

        assigned_ids = {a["member_id"] for s in response.json()["sessions"]
                        for a in s["assignments"]}
        # Weekday — no qualifier filter — regular member should be assignable
        assert regular.id in assigned_ids

    def test_sunday_pool_filter_ignores_roles_with_no_qualifier(
            self, client, db_session):
        """A role with no sunday_qualifier_role should use the full pool on Sundays."""
        soprano = make_role(db_session, "soprano_no_q", display_order=2)
        member = make_member(db_session, "Any", "Soprano", "any_soprano@test.com", [soprano])
        self._setup_sunday_session(db_session)

        with patch.object(settings, 'enable_sunday_pool_filter', True):
            response = client.post("/calendar/schedule/generate",
                                   json={"year": 2026, "month": 4})
        assert response.status_code == 200

        assigned_ids = {a["member_id"] for s in response.json()["sessions"]
                        for a in s["assignments"]}
        assert member.id in assigned_ids



class TestGenerateScheduleNoRoles:
    """generate_schedule should return 422 when no assignable roles are configured."""

    def test_generate_raises_422_when_no_assignable_roles(self, client, db_session):
        # Ensure the only roles in DB have no display_order
        for role in db_session.query(Role).all():
            role.display_order = None
        db_session.commit()

        session = make_program_session(db_session, "Empty Month",
                                       datetime(2026, 11, 1, 10, 0))
        response = client.post("/calendar/schedule/generate",
                               json={"year": 2026, "month": 11})
        assert response.status_code == 422
        assert "assignable roles" in response.json()["detail"].lower()


# ── CSV/PDF export: dynamic columns ───────────────────────────────────────────

class TestDynamicExportColumns:
    """Verify that CSV and PDF exports reflect assignable roles from the DB."""

    def _setup_session_with_assignment(self, db_session, role, year=2026, month=10):
        session = make_program_session(db_session, "Export Test",
                                       datetime(year, month, 4, 10, 0))
        admin = db_session.query(Member).filter(Member.email == "test@example.com").first()
        db_session.add(Assignment(session_id=session.id, member_id=admin.id,
                                  role=role.name))
        db_session.commit()
        return session

    def test_csv_export_header_contains_dynamic_role_names(self, client, db_session):
        custom_role = make_role(db_session, "worship_leader", display_order=1)
        self._setup_session_with_assignment(db_session, custom_role)

        response = client.get("/calendar/schedule/export_csv?year=2026&month=10")
        assert response.status_code == 200

        first_line = response.text.split("\n")[0]
        # Role name should be title-cased in header (worship_leader → Worship Leader)
        assert "Worship Leader" in first_line

    def test_csv_export_header_does_not_contain_removed_role(self, client, db_session):
        """A role without display_order should NOT appear as a column."""
        make_role(db_session, "non_assignable_role_csv", display_order=None)
        make_role(db_session, "assignable_only_csv", display_order=1)
        self._setup_session_with_assignment(
            db_session,
            db_session.query(Role).filter_by(name="assignable_only_csv").first(),
            month=10
        )

        response = client.get("/calendar/schedule/export_csv?year=2026&month=10")
        first_line = response.text.split("\n")[0]
        assert "Non Assignable Role Csv" not in first_line

    def test_pdf_export_returns_200_with_dynamic_roles(self, client, db_session):
        custom_role = make_role(db_session, "cantor", display_order=1)
        session = make_program_session(db_session, "PDF Dynamic",
                                       datetime(2026, 12, 6, 10, 0))
        admin = db_session.query(Member).filter(Member.email == "test@example.com").first()
        db_session.add(Assignment(session_id=session.id, member_id=admin.id,
                                  role=custom_role.name))
        db_session.commit()

        response = client.get("/calendar/schedule/export_pdf?year=2026&month=12")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
