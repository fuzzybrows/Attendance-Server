"""Availability Pydantic schemas."""
from pydantic import BaseModel
from typing import Optional
from schemas.member import Member
from schemas.session import Session

class AvailabilityBase(BaseModel):
    member_id: int
    session_id: int
    is_available: bool = True

class AvailabilityCreate(AvailabilityBase):
    pass

class AvailabilityUpdate(BaseModel):
    is_available: bool

class AvailabilitySchema(AvailabilityBase):
    id: int

    class Config:
        from_attributes = True

class AvailabilityWithDetails(AvailabilitySchema):
    member: Member
    session: Session

    class Config:
        from_attributes = True
