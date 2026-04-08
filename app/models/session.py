import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)  # e.g., "Saturday Rehearsal", "Sunday Service"
    type = Column(String)  # "rehearsal" or "program"
    status = Column(String, default="scheduled")  # "scheduled", "active", "concluded", "archived"
    start_time = Column(DateTime(timezone=True), nullable=False)  # Scheduled start time
    end_time = Column(DateTime(timezone=True), nullable=True)  # Scheduled end time

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Location Geofencing
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    radius = Column(Integer, default=50)  # meters

    attendance = relationship("Attendance", back_populates="session", cascade="all, delete-orphan", passive_deletes=True)


class SessionStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    CONCLUDED = "concluded"
    ARCHIVED = "archived"
