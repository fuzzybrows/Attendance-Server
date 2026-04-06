"""Tests for data models and schemas."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.schemas import (
    MemberCreate, MemberUpdate, SessionCreate, SessionUpdate,
    Token, UnverifiedResponse, LoginResponse,
    AttendanceCreate, Member as MemberSchema,
)
from pydantic import ValidationError
import pytest


class TestMemberSchema:
    def test_member_create_valid(self):
        """Test valid MemberCreate schema."""
        member = MemberCreate(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="secret",
        )
        assert member.first_name == "John"
        assert member.email == "john@example.com"

    def test_member_create_missing_password(self):
        """Test MemberCreate requires password."""
        with pytest.raises(ValidationError):
            MemberCreate(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
            )

    def test_member_update_partial(self):
        """Test MemberUpdate allows partial updates."""
        update = MemberUpdate(first_name="Jane")
        assert update.first_name == "Jane"
        assert update.last_name is None

    def test_member_update_empty(self):
        """Test MemberUpdate with no fields is valid."""
        update = MemberUpdate()
        assert update.first_name is None


class TestSessionSchema:
    def test_session_create_valid(self):
        """Test valid SessionCreate schema."""
        session = SessionCreate(
            title="Rehearsal",
            type="rehearsal",
            start_time="2026-02-15T10:00:00",
            end_time="2026-02-15T12:00:00",
        )
        assert session.title == "Rehearsal"
        assert session.status == "scheduled"  # default

    def test_session_update_partial(self):
        """Test SessionUpdate allows partial updates."""
        update = SessionUpdate(title="Updated")
        assert update.title == "Updated"
        assert update.type is None


class TestLoginResponseUnion:
    def test_unverified_response(self):
        """Test UnverifiedResponse model."""
        resp = UnverifiedResponse(status="unverified", method="email")
        assert resp.status == "unverified"
        assert resp.method == "email"

    def test_unverified_response_missing_field(self):
        """Test UnverifiedResponse requires both fields."""
        with pytest.raises(ValidationError):
            UnverifiedResponse(status="unverified")


class TestAttendanceSchema:
    def test_attendance_create(self):
        """Test AttendanceCreate schema."""
        att = AttendanceCreate(
            member_id=1,
            session_id=1,
            submission_type="nfc",
        )
        assert att.member_id == 1
        assert att.latitude is None  # optional

    def test_attendance_create_with_gps(self):
        """Test AttendanceCreate with GPS data."""
        att = AttendanceCreate(
            member_id=1,
            session_id=1,
            submission_type="manual",
            latitude=29.76,
            longitude=-95.37,
        )
        assert att.latitude == 29.76
