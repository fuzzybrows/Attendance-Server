"""Session-related Pydantic schemas."""
from pydantic import BaseModel, field_serializer
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum


class SessionType(str, Enum):
    REHEARSAL = "rehearsal"
    PROGRAM = "program"


class SessionStatus(str, Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    CONCLUDED = "concluded"
    ARCHIVED = "archived"


class SessionBase(BaseModel):
    model_config = {"use_enum_values": True}
    
    title: str
    type: SessionType
    status: SessionStatus = SessionStatus.SCHEDULED
    start_time: datetime
    end_time: datetime
    # Location
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[int] = 50

    @field_serializer('start_time', 'end_time')
    def serialize_times(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    model_config = {"use_enum_values": True}
    
    title: Optional[str] = None
    type: Optional[SessionType] = None
    status: Optional[SessionStatus] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
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


class SessionMetadata(BaseModel):
    types: List[str]
    statuses: List[str]
