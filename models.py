import enum
import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from database import Base

class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    CONCLUDED = "concluded"
    ARCHIVED = "archived"

class Permission(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"
    EDITOR = "editor"

class Role(str, enum.Enum):
    SOPRANO = "soprano"
    ALTO = "alto"
    TENOR = "tenor"
    BASS = "bass"
    BASS_GUITAR = "bass_guitar"
    KEYBOARD = "keyboard"
    DRUMS = "drums"
    ELECTRIC_GUITAR = "electric_guitar"

class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    firstname = Column(String)
    lastname = Column(String)
    name = Column(String, index=True) # Kept for backward compatibility/concatenation
    email = Column(String, unique=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=True)
    nfc_id = Column(String, unique=True, index=True, nullable=True)
    
    # Roles and Permissions stored as list of strings (JSON)
    roles = Column(JSON, default=[]) # e.g. ["soprano", "keyboard"]
    permissions = Column(JSON, default=["member"]) # Every member has "member" perm
    
    email_verified = Column(Boolean, default=False)
    phone_number_verified = Column(Boolean, default=False)

    attendance = relationship("Attendance", back_populates="member", foreign_keys="[Attendance.member_id]")

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String) # e.g., "Saturday Rehearsal", "Sunday Service"
    type = Column(String) # "rehearsal" or "program"
    status = Column(String, default="active") # "active", "concluded", "archived"
    start_time = Column(DateTime, nullable=False) # Scheduled start time
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    attendance = relationship("Attendance", back_populates="session", cascade="all, delete-orphan", passive_deletes=True)

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # GPS data for manual submission
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    submission_type = Column(String) # "nfc" or "manual"
    marked_by_id = Column(Integer, ForeignKey("members.id"), nullable=True) # Who marked this attendance

    member = relationship("Member", back_populates="attendance", foreign_keys=[member_id])
    marked_by = relationship("Member", foreign_keys=[marked_by_id])
    session = relationship("Session", back_populates="attendance")
