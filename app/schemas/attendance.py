"""Attendance-related Pydantic schemas."""
from pydantic import BaseModel, field_serializer, ConfigDict
from datetime import datetime, timezone
from typing import Optional
from app.schemas.session import Session


class AttendanceBase(BaseModel):
    member_id: int
    session_id: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    submission_type: str  # "nfc" or "manual"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    submission_type: str  # "nfc" or "manual"
    marked_by_id: Optional[int] = None
    device_id: Optional[str] = None


class AttendanceCreate(AttendanceBase):
    pass


class Attendance(AttendanceBase):
    id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes = True)

    @field_serializer('timestamp')
    def serialize_timestamp(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class AttendanceWithSession(Attendance):
    session: Session

    model_config = ConfigDict(from_attributes = True)


class BulkDeleteRequest(BaseModel):
    from typing import List
    ids: List[int]
