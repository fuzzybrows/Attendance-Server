"""QR attendance-related Pydantic schemas."""
from pydantic import BaseModel


class QRTokenResponse(BaseModel):
    token: str
    expires_in: int


class QRMarkResponse(BaseModel):
    status: str
    message: str
    member_name: str
    attendance_id: int
