"""Assignment ORM model."""
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from core.database import Base

class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)

    session = relationship("Session")
    member = relationship("Member")

