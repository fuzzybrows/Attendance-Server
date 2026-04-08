"""Calendar-related Pydantic schemas."""
from pydantic import BaseModel, Field, AliasChoices
from typing import Optional, List, Dict


class DraftScheduleRequest(BaseModel):
    year: int
    month: int


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


class SaveScheduleRequest(BaseModel):
    sessions: List[DraftSessionSchedule]


class DayAvailabilityRequest(BaseModel):
    date: str  # ISO date string, e.g. "2026-03-29"
    is_available: bool = False
