from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas
from core.database import get_db
from core.database import get_db
from core.auth import get_current_user, get_current_active_member

router = APIRouter(
    prefix="/statistics",
    tags=["statistics"],
    responses={404: {"description": "Not found"}},
)


@router.get("/member/{member_id}", response_model=schemas.MemberStatsResponse)
def get_member_stats(member_id: int, db: Session = Depends(get_db), current_member=Depends(get_current_active_member)):
    # Allow if accessing own data or if admin
    is_admin = any(p.name == "admin" for p in current_member.permissions)
    if current_member.id != member_id and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    attendance = db.query(models.Attendance).filter(models.Attendance.member_id == member_id).all()
    sessions = {s.id: s for s in db.query(models.Session).all()}

    history = []
    for a in attendance:
        session = sessions.get(a.session_id)
        status = "prompt" if session and a.timestamp <= session.start_time else "late"
        history.append({
            "session_title": session.title if session else "Unknown",
            "timestamp": a.timestamp,
            "status": status,
            "session_date": session.start_time if session else None
        })

    return {
        "member_name": member.full_name,
        "history": history
    }
