from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class SessionBase(BaseModel):
    title: str
    type: str # "rehearsal" or "program"
    status: str = "active" # "active", "concluded", "archived"
    start_time: datetime

class SessionCreate(SessionBase):
    pass

class SessionUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None

class Session(SessionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class AttendanceBase(BaseModel):
    member_id: int
    session_id: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    submission_type: str # "nfc" or "manual"
    marked_by_id: Optional[int] = None # Who marked this attendance

class AttendanceCreate(AttendanceBase):
    pass

class Attendance(AttendanceBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class AttendanceWithSession(Attendance):
    session: Session

    class Config:
        from_attributes = True

class MemberBase(BaseModel):
    firstname: str
    lastname: str
    email: str
    phone_number: Optional[str] = None
    nfc_id: Optional[str] = None

class MemberCreate(MemberBase):
    password: str

class Member(MemberBase):
    id: int
    name: str # Full name
    roles: List[str] = []
    permissions: List[str] = ["member"]
    email_verified: bool = False
    phone_number_verified: bool = False
    
    class Config:
        from_attributes = True

class MemberUpdate(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    nfc_id: Optional[str] = None
    roles: Optional[List[str]] = None
    permissions: Optional[List[str]] = None

class MemberLogin(BaseModel):
    login: str # email or phone_number
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    member: Member

class TokenData(BaseModel):
    email: Optional[str] = None

class OTPVerification(BaseModel):
    login: str
    otp: str
