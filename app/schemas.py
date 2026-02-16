from pydantic import BaseModel, field_validator, computed_field
from datetime import datetime
from typing import Optional, List, Union

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
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = None
    nfc_id: Optional[str] = None

class MemberCreate(MemberBase):
    password: str

class Member(MemberBase):
    id: int
    
    full_name: str
    # name: str # Full name removed
    roles: List[str] = []
    permissions: List[str] = ["member"]
    email_verified: bool = False
    phone_number_verified: bool = False

    @field_validator('roles', mode='before')
    @classmethod
    def flatten_roles(cls, v):
        if not v:
            return []
        # If it's a list of ORM objects (with .name attribute), flatten them
        return [item.name if hasattr(item, 'name') else item for item in v]

    @field_validator('permissions', mode='before')
    @classmethod
    def flatten_permissions(cls, v):
        if not v:
            return []
        return [item.name if hasattr(item, 'name') else item for item in v]
    
    class Config:
        from_attributes = True

class MemberUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
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

class UnverifiedResponse(BaseModel):
    status: str
    method: str

LoginResponse = Union[Token, UnverifiedResponse]

class TokenData(BaseModel):
    email: Optional[str] = None

class OTPVerification(BaseModel):
    login: str
    otp: str

class AttendanceStats(BaseModel):
    member_id: int
    name: str
    total_sessions: int
    prompt_count: int
    late_count: int
    prompt_rate: float

class SessionHistory(BaseModel):
    session_title: str
    timestamp: datetime
    status: str
    session_date: Optional[datetime] = None

class MemberStatsResponse(BaseModel):
    member_name: str
    history: List[SessionHistory]

class QRTokenResponse(BaseModel):
    token: str
    expires_in: int

class QRMarkResponse(BaseModel):
    status: str
    message: str
    member_name: str
    attendance_id: int

class StatusResponse(BaseModel):
    status: str
