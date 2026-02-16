"""Attendance-related Pydantic schemas."""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from schemas.session import Session


class AttendanceBase(BaseModel):
    member_id: int
    session_id: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    submission_type: str  # "nfc" or "manual"
    marked_by_id: Optional[int] = None


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
