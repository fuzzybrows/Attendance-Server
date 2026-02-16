"""Statistics-related Pydantic schemas."""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


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
