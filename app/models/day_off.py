"""DayOff ORM model – stores day-level unavailability independent of sessions."""
from sqlalchemy import Column, Integer, Date, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class DayOff(Base):
    __tablename__ = "day_offs"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    is_available = Column(Boolean, default=False, nullable=False)

    member = relationship("Member")

    __table_args__ = (
        UniqueConstraint('member_id', 'date', name='uq_member_date_day_off'),
    )
