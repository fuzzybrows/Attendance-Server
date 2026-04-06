"""SessionTemplate API router."""
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, date, timedelta, time, timezone
from app.models.session import Session as SessionModel
from app.models.session_template import SessionTemplate
from app.schemas.session import Session as SessionSchema
from app.schemas.session_template import SessionTemplate as SessionTemplateSchema, SessionTemplateCreate, SessionGenerationRequest
from app.core.database import get_db
from app.core.auth import (
    get_admin_member, 
    get_templates_manager,
    get_schedule_generate_manager
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/session-templates",
    tags=["session_templates"],
)

@router.get("/", response_model=List[SessionTemplateSchema])
def read_templates(db: Session = Depends(get_db), current_member=Depends(get_templates_manager)):
    return db.query(SessionTemplate).all()

@router.post("/", response_model=SessionTemplateSchema)
def create_template(template: SessionTemplateCreate, db: Session = Depends(get_db), current_member=Depends(get_templates_manager)):
    db_template = SessionTemplate(**template.model_dump())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db), current_member=Depends(get_templates_manager)):
    db_template = db.query(SessionTemplate).filter(SessionTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(db_template)
    db.commit()
    return {"status": "success"}

@router.post("/generate", response_model=List[SessionSchema])
def generate_sessions(request: SessionGenerationRequest, db: Session = Depends(get_db), current_member=Depends(get_schedule_generate_manager)):
    """
    Generate sessions for a date range based on active templates.
    """
    try:
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    templates = db.query(SessionTemplate).filter(SessionTemplate.is_active == True).all()
    
    generated_sessions = []
    
    for t in templates:
        frequency = getattr(t, 'frequency', 'weekly')
        valid_dates = []
        
        if frequency == 'daily':
            curr = start_date
            while curr <= end_date:
                valid_dates.append(curr)
                curr += timedelta(days=1)
                
        elif frequency == 'weekly':
            curr = start_date
            while curr <= end_date:
                if curr.weekday() == t.day_of_week:
                    valid_dates.append(curr)
                curr += timedelta(days=1)
                
        elif frequency == 'bi-weekly':
            ref_date = t.reference_start_date or start_date
            anchor = ref_date
            while anchor.weekday() != t.day_of_week:
                anchor += timedelta(days=1)
                
            curr = anchor
            if curr > start_date:
                while curr - timedelta(days=14) >= start_date:
                    curr -= timedelta(days=14)
            else:
                while curr < start_date:
                    curr += timedelta(days=14)
                    
            while curr <= end_date:
                if curr >= start_date:
                    valid_dates.append(curr)
                curr += timedelta(days=14)
                
        elif frequency == 'monthly':
            ref_date = t.reference_start_date or start_date
            anchor = ref_date
            while anchor.weekday() != t.day_of_week:
                anchor += timedelta(days=1)
            week_of_month = (anchor.day - 1) // 7 + 1
            
            curr_year = start_date.year
            curr_month = start_date.month
            end_year = end_date.year
            end_month = end_date.month
            
            while (curr_year, curr_month) <= (end_year, end_month):
                first_day_of_month = date(curr_year, curr_month, 1)
                days_to_add = (t.day_of_week - first_day_of_month.weekday()) % 7
                first_target_day = first_day_of_month + timedelta(days=days_to_add)
                target_day = first_target_day + timedelta(days=7 * (week_of_month - 1))
                
                if target_day.month == curr_month and start_date <= target_day <= end_date:
                    valid_dates.append(target_day)
                    
                if curr_month == 12:
                    curr_month = 1
                    curr_year += 1
                else:
                    curr_month += 1
                    
        LOCAL_TZ = ZoneInfo("America/Chicago")
        
        for d in valid_dates:
            # Create a localized datetime in Austin time
            local_start = datetime.combine(d, t.start_time).replace(tzinfo=LOCAL_TZ)
            # Convert to UTC-aware for database storage
            start_time = local_start.astimezone(timezone.utc)
            
            local_end = datetime.combine(d, t.end_time).replace(tzinfo=LOCAL_TZ)
            if t.end_time < t.start_time:
                local_end += timedelta(days=1)
            end_time = local_end.astimezone(timezone.utc)
                
            existing = db.query(SessionModel).filter(
                SessionModel.start_time == start_time,
                SessionModel.title == t.title
            ).first()
            
            if not existing:
                db_session = SessionModel(
                    title=t.title,
                    type=t.type,
                    status="scheduled",
                    start_time=start_time,
                    end_time=end_time,
                    latitude=t.latitude,
                    longitude=t.longitude,
                    radius=t.radius
                )
                db.add(db_session)
                generated_sessions.append(db_session)
    
    db.commit()
    for s in generated_sessions:
        db.refresh(s)
    
    logger.info(f"Generated {len(generated_sessions)} sessions from templates", extra={"type": "sessions_generated", "count": len(generated_sessions)})
    return generated_sessions
