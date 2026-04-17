"""Authentication-related Pydantic schemas."""
from pydantic import BaseModel, field_validator
from typing import Optional, Union
from app.schemas.member import Member


def _normalize_login(v: str) -> str:
    """Strip whitespace and lowercase email logins for case-insensitive lookups."""
    v = v.strip()
    return v.lower() if "@" in v else v


class MemberLogin(BaseModel):
    login: str  # email or phone_number
    password: str
    recaptcha_token: Optional[str] = None

    @field_validator("login")
    @classmethod
    def normalize_login(cls, v: str) -> str:
        return _normalize_login(v)

class ForgotPasswordRequest(BaseModel):
    login: str
    recaptcha_token: Optional[str] = None

    @field_validator("login")
    @classmethod
    def normalize_login(cls, v: str) -> str:
        return _normalize_login(v)


class Token(BaseModel):
    access_token: str
    token_type: str
    member: Member


class UnverifiedResponse(BaseModel):
    status: str
    method: str


LoginResponse = Union[Token, UnverifiedResponse]


class TokenData(BaseModel):
    email: Optional[str] = None


class OTPVerification(BaseModel):
    login: str
    otp: str

    @field_validator("login")
    @classmethod
    def normalize_login(cls, v: str) -> str:
        return _normalize_login(v)


class ResetPasswordRequest(BaseModel):
    login: str
    otp: str
    new_password: str

    @field_validator("login")
    @classmethod
    def normalize_login(cls, v: str) -> str:
        return _normalize_login(v)


class StatusResponse(BaseModel):
    status: str
