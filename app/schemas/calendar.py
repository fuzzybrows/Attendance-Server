"""Calendar-related Pydantic schemas."""
from pydantic import BaseModel, Field, AliasChoices
from typing import Optional, List, Dict


class DraftScheduleRequest(BaseModel):
    year: int
    month: int
    # Optional: if provided, only auto-fill these roles (applied globally).
    # If None, all assignable roles are used (original behaviour).
    roles: Optional[List[str]] = None
    # Optional: per-session role overrides  { session_id: ["role1", "role2"] }
    # If a session_id is present here, its list takes precedence over `roles`.
    session_overrides: Optional[Dict[int, List[str]]] = None


class DraftAssignment(BaseModel):
    member_id: int
    member_name: Optional[str] = None
    role: str


class DraftSessionSchedule(BaseModel):
    id: int = Field(validation_alias=AliasChoices('id', 'session_id'))
    title: str = Field(validation_alias=AliasChoices('title', 'session_title'))
    start_time: str
    type: str
    assignments: List[DraftAssignment]


class DraftScheduleResponse(BaseModel):
    sessions: List[DraftSessionSchedule]
    month_locked: bool = False
    schedule_notified_at: str | None = None


class SaveScheduleRequest(BaseModel):
    sessions: List[DraftSessionSchedule]


class DayAvailabilityRequest(BaseModel):
    date: str  # ISO date string, e.g. "2026-03-29"
    is_available: bool = False
