"""SessionTemplate Pydantic schemas."""
from pydantic import BaseModel, ConfigDict
from datetime import time, date
from typing import Optional, List, Literal
from .session import SessionType

class SessionTemplateBase(BaseModel):
    title: str
    type: SessionType
    day_of_week: int  # 0=Monday, 6=Sunday
    frequency: Literal["daily", "weekly", "bi-weekly", "monthly"] = "weekly"
    reference_start_date: Optional[date] = None
    start_time: time
    end_time: time
    
    # Geofencing defaults
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[int] = 50
    
    is_active: bool = True

class SessionTemplateCreate(SessionTemplateBase):
    pass

class SessionTemplateUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[SessionType] = None
    day_of_week: Optional[int] = None
    frequency: Optional[Literal["daily", "weekly", "bi-weekly", "monthly"]] = None
    reference_start_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[int] = None
    is_active: Optional[bool] = None

class SessionTemplate(SessionTemplateBase):
    id: int

    model_config = ConfigDict(from_attributes = True)

class SessionGenerationRequest(BaseModel):
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
