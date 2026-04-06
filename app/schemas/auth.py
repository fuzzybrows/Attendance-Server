"""Authentication-related Pydantic schemas."""
from pydantic import BaseModel
from typing import Optional, Union
from app.schemas.member import Member


class MemberLogin(BaseModel):
    login: str  # email or phone_number
    password: str
    recaptcha_token: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    login: str
    recaptcha_token: Optional[str] = None


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


class StatusResponse(BaseModel):
    status: str
