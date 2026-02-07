from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class AttendanceBase(BaseModel):
    member_id: int
    session_id: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    submission_type: str # "nfc" or "manual"

class AttendanceCreate(AttendanceBase):
    pass

class Attendance(AttendanceBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class MemberBase(BaseModel):
    name: str
    email: str
    nfc_id: Optional[str] = None

class MemberCreate(MemberBase):
    pass

class Member(MemberBase):
    id: int
    
    class Config:
        from_attributes = True

class SessionBase(BaseModel):
    title: str
    type: str # "rehearsal" or "program"
    date: datetime

class SessionCreate(SessionBase):
    pass

class Session(SessionBase):
    id: int

    class Config:
        from_attributes = True
