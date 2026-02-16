"""Session ORM model."""
import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from core.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)  # e.g., "Saturday Rehearsal", "Sunday Service"
    type = Column(String)  # "rehearsal" or "program"
    status = Column(String, default="active")  # "active", "concluded", "archived"
    start_time = Column(DateTime, nullable=False)  # Scheduled start time
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    attendance = relationship("Attendance", back_populates="session", cascade="all, delete-orphan", passive_deletes=True)
