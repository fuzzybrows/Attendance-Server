"""
Schemas package — re-exports all Pydantic schemas for convenient import.
Usage: `import schemas` continues to work as before.
"""
from schemas.member import MemberBase, MemberCreate, Member, MemberUpdate, MemberMetadata
from schemas.session import SessionBase, SessionCreate, SessionUpdate, Session, SessionMetadata
from schemas.attendance import AttendanceBase, AttendanceCreate, Attendance, AttendanceWithSession
from schemas.auth import MemberLogin, Token, UnverifiedResponse, LoginResponse, TokenData, OTPVerification, StatusResponse, ForgotPasswordRequest
from schemas.stats import AttendanceStats, SessionHistory, MemberStatsResponse
from schemas.qr import QRTokenResponse, QRMarkResponse
from schemas.availability import AvailabilityBase, AvailabilityCreate, AvailabilityUpdate, AvailabilitySchema, AvailabilityWithDetails
from schemas.assignment import AssignmentBase, AssignmentCreate, AssignmentSchema, AssignmentWithDetails
from schemas import session_template

__all__ = [
    # Member
    "MemberBase", "MemberCreate", "Member", "MemberUpdate", "MemberMetadata",
    # Session
    "SessionBase", "SessionCreate", "SessionUpdate", "Session", "SessionMetadata",
    # Attendance
    "AttendanceBase", "AttendanceCreate", "Attendance", "AttendanceWithSession",
    # Auth
    "MemberLogin", "Token", "UnverifiedResponse", "LoginResponse",
    "TokenData", "OTPVerification", "StatusResponse", "ForgotPasswordRequest",
    # Stats
    "AttendanceStats", "SessionHistory", "MemberStatsResponse",
    # QR
    "QRTokenResponse", "QRMarkResponse",
    # Availability
    "AvailabilityBase", "AvailabilityCreate", "AvailabilityUpdate", "AvailabilitySchema", "AvailabilityWithDetails",
    # Assignment
    "AssignmentBase", "AssignmentCreate", "AssignmentSchema", "AssignmentWithDetails",
    "session_template",
]
