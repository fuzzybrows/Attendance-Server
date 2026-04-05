"""Assignment Pydantic schemas."""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from schemas.member import Member
from schemas.session import Session

class AssignmentBase(BaseModel):
    session_id: int
    member_id: int
    role: str

class AssignmentCreate(AssignmentBase):
    pass

class AssignmentSchema(AssignmentBase):
    id: int

    model_config = ConfigDict(from_attributes = True)

class AssignmentWithDetails(AssignmentSchema):
    session: Session
    member: Member

    model_config = ConfigDict(from_attributes = True)
