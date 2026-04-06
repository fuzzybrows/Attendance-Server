"""Tests for data models and schemas."""
import os
from app.schemas.member import MemberCreate, MemberUpdate, Member as MemberSchema
from app.schemas.session import SessionCreate, SessionUpdate
from app.schemas.auth import Token, UnverifiedResponse, LoginResponse
from app.schemas.attendance import AttendanceCreate
from pydantic import ValidationError
import pytest


class TestMemberSchema:
    def test_member_create_schema_successfully_validates_complete_data(self):
        member = MemberCreate(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="secret",
        )
        assert member.first_name == "John"
        assert member.email == "john@example.com"

    def test_member_create_schema_raises_validation_error_when_password_is_missing(self):
        with pytest.raises(ValidationError):
            MemberCreate(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
            )

    def test_member_update_schema_allows_and_correctly_handles_partial_field_updates(self):
        update = MemberUpdate(first_name="Jane")
        assert update.first_name == "Jane"
        assert update.last_name is None

    def test_member_update_schema_is_valid_when_instantiated_with_no_fields(self):
        update = MemberUpdate()
        assert update.first_name is None


class TestSessionSchema:
    def test_session_create_schema_successfully_validates_complete_data_with_defaults(self):
        session = SessionCreate(
            title="Rehearsal",
            type="rehearsal",
            start_time="2026-02-15T10:00:00",
            end_time="2026-02-15T12:00:00",
        )
        assert session.title == "Rehearsal"
        assert session.status == "scheduled"  # default

    def test_session_update_schema_allows_and_correctly_handles_partial_field_updates(self):
        update = SessionUpdate(title="Updated")
        assert update.title == "Updated"
        assert update.type is None


class TestLoginResponseUnion:
    def test_unverified_response_schema_correctly_holds_status_and_method_fields(self):
        resp = UnverifiedResponse(status="unverified", method="email")
        assert resp.status == "unverified"
        assert resp.method == "email"

    def test_unverified_response_schema_raises_validation_error_when_required_fields_are_missing(self):
        with pytest.raises(ValidationError):
            UnverifiedResponse(status="unverified")


class TestAttendanceSchema:
    def test_attendance_create_schema_successfully_validates_minimal_required_data(self):
        att = AttendanceCreate(
            member_id=1,
            session_id=1,
            submission_type="nfc",
        )
        assert att.member_id == 1
        assert att.latitude is None  # optional

    def test_attendance_create_schema_correctly_validates_and_stores_optional_gps_coordinates(self):
        att = AttendanceCreate(
            member_id=1,
            session_id=1,
            submission_type="manual",
            latitude=29.76,
            longitude=-95.37,
        )
        assert att.latitude == 29.76
