"""Availability Pydantic schemas."""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from app.schemas.member import Member
from app.schemas.session import Session

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

    model_config = ConfigDict(from_attributes = True)

class AvailabilityWithDetails(AvailabilitySchema):
    member: Member
    session: Session

    model_config = ConfigDict(from_attributes = True)
