from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.models import Member, Session as SessionModel
from app.schemas.session import Session as SessionSchema, SessionCreate, SessionUpdate, SessionMetadata, SessionType, SessionStatus
from datetime import timezone
from app.core.database import get_db
from app.core.database import get_db
from app.core.auth import (
    get_current_user, 
    get_admin_member, 
    get_sessions_read_manager, 
    get_sessions_create_manager, 
    get_sessions_edit_manager, 
    get_sessions_delete_manager
)
import logging

logger = logging.getLogger(__name__)

class BulkDeleteRequest(BaseModel):
    ids: List[int]

router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
    responses={404: {"description": "Not found"}},
)

@router.get("/metadata", response_model=SessionMetadata)
def get_session_metadata(current_member=Depends(get_sessions_read_manager)):
    """
    Get all available session types and statuses from the Enums.
    """
    return {
        "types": [t.value for t in SessionType],
        "statuses": [s.value for s in SessionStatus]
    }

@router.post("/", response_model=SessionSchema)
def create_session(session: SessionCreate, db: Session = Depends(get_db), current_member=Depends(get_sessions_create_manager)):
    logger.info("Creating session", extra={"type": "session_create_attempt", "title": session.title, "session_type": session.type})
    
    if session.status == "active":
        db.query(SessionModel).filter(SessionModel.status == "active").update({"status": "concluded"})
        
    start_time = session.start_time
    if start_time and start_time.tzinfo is not None:
        start_time = start_time.astimezone(timezone.utc).replace(tzinfo=None)

    db_session = SessionModel(
        title=session.title, 
        type=session.type,
        status=session.status,
        start_time=start_time,
        end_time=session.end_time,
        latitude=session.latitude,
        longitude=session.longitude,
        radius=session.radius
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    logger.info("Session created successfully", extra={"type": "session_create_success", "session_id": db_session.id})
    return db_session

@router.get("/", response_model=List[SessionSchema])
def read_sessions(
    skip: int = 0, 
    limit: int = 100, 
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db), 
    _current_user: Member = Depends(get_sessions_read_manager)
):
    query = db.query(SessionModel)
    
    if start_date:
        try:
            from datetime import datetime
            sd = datetime.fromisoformat(start_date.replace('Z', '+00:00')).astimezone(timezone.utc).replace(tzinfo=None)
            query = query.filter(SessionModel.start_time >= sd)
        except ValueError:
            pass
            
    if end_date:
        try:
            from datetime import datetime
            ed = datetime.fromisoformat(end_date.replace('Z', '+00:00')).astimezone(timezone.utc).replace(tzinfo=None)
            query = query.filter(SessionModel.start_time <= ed)
        except ValueError:
            pass

    sessions = query.order_by(SessionModel.start_time.desc()).offset(skip).limit(limit).all()
    return sessions

@router.patch("/{session_id}", response_model=SessionSchema)
def update_session(session_id: int, update: SessionUpdate, db: Session = Depends(get_db), current_member=Depends(get_sessions_edit_manager)):
    logger.info("Updating session", extra={"type": "session_update", "session_id": session_id, "admin": current_member.email})
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        if field == "start_time" and value.tzinfo is not None:
            # Force naive UTC to prevent SQLAlchemy/SQLite implicit offset shifts
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        setattr(session, field, value)
    db.commit()
    db.refresh(session)
    return session

@router.delete("/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db), current_member=Depends(get_sessions_delete_manager)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"status": "deleted", "session_id": session_id}

@router.post("/bulk-delete")
def bulk_delete_sessions(request: BulkDeleteRequest, db: Session = Depends(get_db), current_member=Depends(get_sessions_delete_manager)):
    if not request.ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
    logger.warning("Bulk deleting sessions", extra={"type": "session_bulk_delete", "ids": request.ids})
    deleted = db.query(SessionModel).filter(SessionModel.id.in_(request.ids)).delete(synchronize_session='fetch')
    db.commit()
    return {"status": "deleted", "count": deleted}
