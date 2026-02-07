from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    nfc_id = Column(String, unique=True, index=True, nullable=True)

    attendance = relationship("Attendance", back_populates="member")

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String) # e.g., "Saturday Rehearsal", "Sunday Service"
    type = Column(String) # "rehearsal" or "program"
    date = Column(DateTime, default=datetime.datetime.utcnow)

    attendance = relationship("Attendance", back_populates="session")

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    session_id = Column(Integer, ForeignKey("sessions.id"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # GPS data for manual submission
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    submission_type = Column(String) # "nfc" or "manual"

    member = relationship("Member", back_populates="attendance")
    session = relationship("Session", back_populates="attendance")
