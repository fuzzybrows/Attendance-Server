"""Session-related Pydantic schemas."""
from pydantic import BaseModel, field_serializer
from datetime import datetime, timezone
from typing import Optional


class SessionBase(BaseModel):
    title: str
    type: str  # "rehearsal" or "program"
    status: str = "active"  # "active", "concluded", "archived"
    start_time: datetime
    # Location
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[int] = 50

    @field_serializer('start_time')
    def serialize_start_time(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    start_time: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[int] = None


class Session(SessionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('created_at')
    def serialize_created_at(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
