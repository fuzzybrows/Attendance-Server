"""Availability ORM model."""
from sqlalchemy import Column, Integer, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base

class Availability(Base):
    __tablename__ = "availabilities"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)

    member = relationship("Member")
    session = relationship("Session")

    __table_args__ = (
        UniqueConstraint('member_id', 'session_id', name='uq_member_session_availability'),
    )
