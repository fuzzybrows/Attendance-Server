"""SessionTemplate ORM model."""
from sqlalchemy import Column, Integer, String, Time, Boolean, Float, Date
from core.database import Base

class SessionTemplate(Base):
    __tablename__ = "session_templates"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False)  # "rehearsal" or "program"
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    frequency = Column(String, nullable=False, default="weekly")  # "daily", "weekly", "bi-weekly", "monthly"
    reference_start_date = Column(Date, nullable=True)  # Used for bi-weekly/monthly calculations
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=True)
    
    # Geofencing defaults
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    radius = Column(Integer, default=50)
    
    is_active = Column(Boolean, default=True)
