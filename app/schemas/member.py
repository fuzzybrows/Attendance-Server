"""Member-related Pydantic schemas."""
from pydantic import BaseModel, field_validator
from typing import Optional, List


class MemberBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = None
    nfc_id: Optional[str] = None


class MemberCreate(MemberBase):
    password: str


class Member(MemberBase):
    id: int
    full_name: str
    roles: List[str] = []
    permissions: List[str] = ["member"]
    email_verified: bool = False
    phone_number_verified: bool = False

    @field_validator('roles', mode='before')
    @classmethod
    def flatten_roles(cls, v):
        if not v:
            return []
        return [item.name if hasattr(item, 'name') else item for item in v]

    @field_validator('permissions', mode='before')
    @classmethod
    def flatten_permissions(cls, v):
        if not v:
            return []
        return [item.name if hasattr(item, 'name') else item for item in v]

    class Config:
        from_attributes = True


class MemberUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    nfc_id: Optional[str] = None
    roles: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
