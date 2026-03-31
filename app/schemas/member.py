"""Member-related Pydantic schemas."""
from pydantic import BaseModel, field_validator
from typing import Optional, List


class MemberBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = None
    nfc_id: Optional[str] = None

    @field_validator('phone_number', 'nfc_id', mode='before')
    @classmethod
    def convert_empty_to_none(cls, v):
        return None if (v == "" or str(v).strip() == "") else v


class MemberCreate(MemberBase):
    password: str
    roles: List[str] = []
    permissions: List[str] = ["member"]


class Member(MemberBase):
    id: int
    full_name: str
    roles: List[str] = []
    permissions: List[str] = ["member"]
    email_verified: Optional[bool] = False
    phone_number_verified: Optional[bool] = False

    @field_validator('email_verified', 'phone_number_verified', mode='before')
    @classmethod
    def coerce_none_to_false(cls, v):
        return v if v is not None else False

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


class MemberMetadata(BaseModel):
    roles: List[str]
    permissions: List[str]
