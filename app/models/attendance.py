"""Attendance ORM model."""
import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    # Device Fingerprint
    device_id = Column(String, nullable=True)

    # GPS data for manual submission
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    submission_type = Column(String)  # "nfc" or "manual"
    marked_by_id = Column(Integer, ForeignKey("members.id"), nullable=True)

    member = relationship("Member", back_populates="attendance", foreign_keys=[member_id])
    marked_by = relationship("Member", foreign_keys=[marked_by_id])
    session = relationship("Session", back_populates="attendance")
