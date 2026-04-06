"""
Schemas package — re-exports all Pydantic schemas for convenient import.
Usage: `import schemas` continues to work as before.
"""
from app.schemas.member import MemberBase, MemberCreate, Member, MemberUpdate, MemberMetadata
from app.schemas.session import SessionBase, SessionCreate, SessionUpdate, Session, SessionMetadata
from app.schemas.attendance import AttendanceBase, AttendanceCreate, Attendance, AttendanceWithSession
from app.schemas.auth import MemberLogin, Token, UnverifiedResponse, LoginResponse, TokenData, OTPVerification, StatusResponse, ForgotPasswordRequest
from app.schemas.stats import AttendanceStats, SessionHistory, MemberStatsResponse
from app.schemas.qr import QRTokenResponse, QRMarkResponse
from app.schemas.availability import AvailabilityBase, AvailabilityCreate, AvailabilityUpdate, AvailabilitySchema, AvailabilityWithDetails
from app.schemas.assignment import AssignmentBase, AssignmentCreate, AssignmentSchema, AssignmentWithDetails
from app.schemas import session_template

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
