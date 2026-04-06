"""QR attendance-related Pydantic schemas."""
from pydantic import BaseModel
from typing import Optional


class QRTokenResponse(BaseModel):
    token: str
    expires_in: int


class QRMarkPayload(BaseModel):
    device_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class QRMarkResponse(BaseModel):
    status: str
    message: str
    member_name: str
    attendance_id: int
