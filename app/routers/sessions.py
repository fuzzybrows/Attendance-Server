from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import models, schemas
from datetime import timezone
from core.database import get_db
from core.database import get_db
from core.auth import get_current_user, get_admin_member
import logging

logger = logging.getLogger(__name__)

class BulkDeleteRequest(BaseModel):
    ids: List[int]

router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
    responses={404: {"description": "Not found"}},
)

@router.get("/metadata", response_model=schemas.SessionMetadata)
def get_session_metadata(current_member=Depends(get_admin_member)):
    """
    Get all available session types and statuses from the Enums.
    """
    return {
        "types": [t.value for t in schemas.session.SessionType],
        "statuses": [s.value for s in schemas.session.SessionStatus]
    }

@router.post("/", response_model=schemas.Session)
def create_session(session: schemas.SessionCreate, db: Session = Depends(get_db), current_member=Depends(get_admin_member)):
    logger.info("Creating session", extra={"type": "session_create_attempt", "title": session.title, "session_type": session.type})
    
    if session.status == "active":
        db.query(models.Session).filter(models.Session.status == "active").update({"status": "concluded"})
        
    start_time = session.start_time
    if start_time and start_time.tzinfo is not None:
        start_time = start_time.astimezone(timezone.utc).replace(tzinfo=None)

    db_session = models.Session(
        title=session.title, 
        type=session.type,
        status=session.status,
        start_time=start_time,
        latitude=session.latitude,
        longitude=session.longitude,
        radius=session.radius
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    logger.info("Session created successfully", extra={"type": "session_create_success", "session_id": db_session.id})
    return db_session

@router.get("/", response_model=List[schemas.Session])
def read_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _current_user: str = Depends(get_current_user)):
    sessions = db.query(models.Session).order_by(models.Session.start_time.desc()).offset(skip).limit(limit).all()
    return sessions

@router.patch("/{session_id}", response_model=schemas.Session)
def update_session(session_id: int, update: schemas.SessionUpdate, db: Session = Depends(get_db), current_member=Depends(get_admin_member)):
    logger.info("Updating session", extra={"type": "session_update", "session_id": session_id, "admin": current_member.email})
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
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
def delete_session(session_id: int, db: Session = Depends(get_db), current_member=Depends(get_admin_member)):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"status": "deleted", "session_id": session_id}

@router.post("/bulk-delete")
def bulk_delete_sessions(request: BulkDeleteRequest, db: Session = Depends(get_db), current_member=Depends(get_admin_member)):
    if not request.ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
    logger.warning("Bulk deleting sessions", extra={"type": "session_bulk_delete", "ids": request.ids})
    deleted = db.query(models.Session).filter(models.Session.id.in_(request.ids)).delete(synchronize_session='fetch')
    db.commit()
    return {"status": "deleted", "count": deleted}
