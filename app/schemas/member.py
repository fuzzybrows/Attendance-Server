"""Member-related Pydantic schemas."""
from pydantic import BaseModel, field_validator, Field, ConfigDict
from typing import Optional, List, Dict
import re


def _validate_preferred_firstname(v):
    """Shared validation for preferred_displayed_firstname."""
    if v is None or (isinstance(v, str) and v.strip() == ''):
        return None
    v = v.strip()
    if len(v) < 3:
        raise ValueError('Preferred first name must be at least 3 characters')
    if not re.match(r'^[A-Za-z\s\-]+$', v):
        raise ValueError('Preferred first name must contain only letters, spaces, or hyphens')
    return v.title()


class MemberBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = None
    nfc_id: Optional[str] = None
    is_active: bool = True
    birth_month: Optional[int] = None
    birth_day: Optional[int] = None
    birth_year: Optional[int] = None
    tshirt_size: Optional[str] = None
    address_street: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_zip: Optional[str] = None
    preferred_displayed_firstname: Optional[str] = None

    @field_validator('preferred_displayed_firstname', mode='before')
    @classmethod
    def validate_preferred_firstname(cls, v):
        return _validate_preferred_firstname(v)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator('phone_number', 'nfc_id', mode='before')
    @classmethod
    def convert_empty_to_none(cls, v):
        return None if (v == "" or str(v).strip() == "") else v

    @field_validator('birth_month', mode='before')
    @classmethod
    def validate_birth_month(cls, v):
        if v is None or v == '':
            return None
        v = int(v)
        if not 1 <= v <= 12:
            raise ValueError('Birth month must be between 1 and 12')
        return v

    @field_validator('birth_day', mode='before')
    @classmethod
    def validate_birth_day(cls, v):
        if v is None or v == '':
            return None
        v = int(v)
        if not 1 <= v <= 31:
            raise ValueError('Birth day must be between 1 and 31')
        return v


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
    display_first_name: str = ''
    preferred_displayed_firstname: Optional[str] = None

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

    model_config = ConfigDict(from_attributes = True)


class RoleSchema(BaseModel):
    name: str
    description: Optional[str] = None
    display_order: Optional[int] = Field(default=None, description="Display order for assignable roles. If set, the role is assignable in session scheduling.")
    is_assignable: bool = Field(default=False, description="Whether members with this role can be assigned in session scheduling.")
    
    model_config = ConfigDict(from_attributes = True)


class MemberUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    nfc_id: Optional[str] = None
    roles: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None
    birth_month: Optional[int] = None
    birth_day: Optional[int] = None
    birth_year: Optional[int] = None
    tshirt_size: Optional[str] = None
    address_street: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_zip: Optional[str] = None
    preferred_displayed_firstname: Optional[str] = None

    @field_validator('preferred_displayed_firstname', mode='before')
    @classmethod
    def validate_preferred_firstname(cls, v):
        return _validate_preferred_firstname(v)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower() if v is not None else v

    @field_validator('birth_month', mode='before')
    @classmethod
    def validate_birth_month(cls, v):
        if v is None or v == '':
            return None
        v = int(v)
        if not 1 <= v <= 12:
            raise ValueError('Birth month must be between 1 and 12')
        return v

    @field_validator('birth_day', mode='before')
    @classmethod
    def validate_birth_day(cls, v):
        if v is None or v == '':
            return None
        v = int(v)
        if not 1 <= v <= 31:
            raise ValueError('Birth day must be between 1 and 31')
        return v


class ProfileUpdate(BaseModel):
    """Self-service profile update — users can only change their own non-privileged fields."""
    birth_month: Optional[int] = None
    birth_day: Optional[int] = None
    birth_year: Optional[int] = None
    tshirt_size: Optional[str] = None
    address_street: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_zip: Optional[str] = None
    preferred_displayed_firstname: Optional[str] = None

    @field_validator('preferred_displayed_firstname', mode='before')
    @classmethod
    def validate_preferred_firstname(cls, v):
        return _validate_preferred_firstname(v)

    @field_validator('birth_month', mode='before')
    @classmethod
    def validate_birth_month(cls, v):
        if v is None or v == '':
            return None
        v = int(v)
        if not 1 <= v <= 12:
            raise ValueError('Birth month must be between 1 and 12')
        return v

    @field_validator('birth_day', mode='before')
    @classmethod
    def validate_birth_day(cls, v):
        if v is None or v == '':
            return None
        v = int(v)
        if not 1 <= v <= 31:
            raise ValueError('Birth day must be between 1 and 31')
        return v


class PasswordResetRequest(BaseModel):
    new_password: str


class MemberMetadata(BaseModel):
    roles: List[str]
    permissions: List[str]
    assignable_roles: List[str]
    sunday_qualifiers: Dict[str, str] = Field(
        default={},
        description=(
            "Maps each assignable role name to the qualifier role name a member must also hold "
            "to fill that slot on Sundays (e.g. {\"lead_singer\": \"Sunday Lead Singer\"}). "
            "Empty when no sunday_qualifier_role FK is configured on any role."
        ),
    )
    enable_sunday_pool_filter: bool = Field(
        default=True,
        description=(
            "Scenario 1 flag (ENABLE_SUNDAY_POOL_FILTER). "
            "When true, the schedule generator narrows the eligible member pool on Sundays "
            "to those who also hold the role's configured sunday_qualifier_role. "
            "When false, all role-holders are eligible regardless of day."
        ),
    )
    enable_sunday_preview_defaults: bool = Field(
        default=True,
        description=(
            "Scenario 2 flag (ENABLE_SUNDAY_PREVIEW_DEFAULTS). "
            "When true, the generation preview modal pre-selects all roles for Sunday programs "
            "and only the primary role for weekday programs. "
            "When false, all roles are pre-selected for every program session."
        ),
    )


class PhoneChangeRequest(BaseModel):
    phone_number: str


class PhoneVerifyRequest(BaseModel):
    phone_number: str
    otp: str
