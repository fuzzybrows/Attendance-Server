"""MonthLock ORM model – stores explicit month-level availability lock state."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Boolean, DateTime, UniqueConstraint
from app.core.database import Base


class MonthLock(Base):
    __tablename__ = "month_locks"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    is_locked = Column(Boolean, nullable=False, default=True)

    # Tracks when schedule-published notifications were last sent for this month
    notified_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint('year', 'month', name='uq_year_month_lock'),
    )
