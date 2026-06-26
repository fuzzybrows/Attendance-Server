"""MonthLock ORM model – stores explicit month-level availability lock state."""
from sqlalchemy import Column, Integer, Boolean, UniqueConstraint
from app.core.database import Base


class MonthLock(Base):
    __tablename__ = "month_locks"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    is_locked = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint('year', 'month', name='uq_year_month_lock'),
    )
