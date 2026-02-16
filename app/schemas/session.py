"""Session-related Pydantic schemas."""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class SessionBase(BaseModel):
    title: str
    type: str  # "rehearsal" or "program"
    status: str = "active"  # "active", "concluded", "archived"
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
