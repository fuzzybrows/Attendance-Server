"""
Schemas package — re-exports all Pydantic schemas for convenient import.
Usage: `import schemas` continues to work as before.
"""
from schemas.member import MemberBase, MemberCreate, Member, MemberUpdate
from schemas.session import SessionBase, SessionCreate, SessionUpdate, Session
from schemas.attendance import AttendanceBase, AttendanceCreate, Attendance, AttendanceWithSession
from schemas.auth import MemberLogin, Token, UnverifiedResponse, LoginResponse, TokenData, OTPVerification, StatusResponse
from schemas.stats import AttendanceStats, SessionHistory, MemberStatsResponse
from schemas.qr import QRTokenResponse, QRMarkResponse

__all__ = [
    # Member
    "MemberBase", "MemberCreate", "Member", "MemberUpdate",
    # Session
    "SessionBase", "SessionCreate", "SessionUpdate", "Session",
    # Attendance
    "AttendanceBase", "AttendanceCreate", "Attendance", "AttendanceWithSession",
    # Auth
    "MemberLogin", "Token", "UnverifiedResponse", "LoginResponse",
    "TokenData", "OTPVerification", "StatusResponse",
    # Stats
    "AttendanceStats", "SessionHistory", "MemberStatsResponse",
    # QR
    "QRTokenResponse", "QRMarkResponse",
]
