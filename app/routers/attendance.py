from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from pydantic import BaseModel
import models, schemas
from core.database import get_db
from core.database import get_db
from core.auth import (
    get_current_user, 
    get_admin_member, 
    get_current_active_member,
    get_attendance_read_manager,
    get_attendance_write_manager,
    get_attendance_delete_manager
)
import logging

logger = logging.getLogger(__name__)

class BulkDeleteRequest(BaseModel):
    ids: List[int]

router = APIRouter(
    prefix="/attendance",
    tags=["attendance"],
    responses={404: {"description": "Not found"}},
)

from services.attendance import validate_attendance

@router.post("/", response_model=schemas.Attendance)
def mark_attendance(attendance: schemas.AttendanceCreate, db: Session = Depends(get_db), current_member=Depends(get_attendance_write_manager)):
    logger.info("Marking attendance", extra={
        "type": "attendance_mark_attempt",
        "member_id": attendance.member_id,
        "session_id": attendance.session_id,
        "device_id": attendance.device_id
    })

    # Verify member and session exist
    member = db.query(models.Member).filter(models.Member.id == attendance.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    session = db.query(models.Session).filter(models.Session.id == attendance.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Fraud Prevention & Validation
    validate_attendance(
        db=db,
        session=session,
        member_id=attendance.member_id,
        device_id=attendance.device_id,
        latitude=attendance.latitude,
        longitude=attendance.longitude,
        marked_by_id=attendance.marked_by_id
    )

    db_attendance = models.Attendance(
        member_id=attendance.member_id,
        session_id=attendance.session_id,
        latitude=attendance.latitude,
        longitude=attendance.longitude,
        submission_type=attendance.submission_type,
        marked_by_id=attendance.marked_by_id,
        device_id=attendance.device_id
    )
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)
    return db_attendance

@router.get("/session/{session_id}", response_model=List[schemas.Attendance])
def read_attendance(session_id: int, db: Session = Depends(get_db), current_member=Depends(get_current_active_member)):
    # Note: Keep get_current_active_member to allow mobile users to resolve names for their own session.
    # However, for administrative lists, we should use get_attendance_read_manager.
    # For now, we'll keep this as-is for mobile app compatibility but update the stats route below.
    # Allow all authenticated members to view session attendance (for mobile app)
    attendance = db.query(models.Attendance).filter(models.Attendance.session_id == session_id).all()
    return attendance

@router.get("/member/{member_id}", response_model=List[schemas.AttendanceWithSession])
def get_member_attendance(member_id: int, db: Session = Depends(get_db), current_member=Depends(get_current_active_member)):
    # Allow if accessing own data or if admin
    is_admin = any(p.name == "admin" for p in current_member.permissions)
    if current_member.id != member_id and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        attendance = db.query(models.Attendance)\
            .join(models.Session)\
            .options(joinedload(models.Attendance.session))\
            .filter(models.Attendance.member_id == member_id)\
            .order_by(models.Attendance.timestamp.desc())\
            .all()
        return attendance
    except Exception as e:
        logger.error(f"Error fetching member attendance: {str(e)}", exc_info=True, extra={"type": "attendance_read_error", "member_id": member_id})
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.delete("/{attendance_id}")
def delete_attendance(attendance_id: int, db: Session = Depends(get_db), current_member=Depends(get_attendance_delete_manager)):
    attendance = db.query(models.Attendance).filter(models.Attendance.id == attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    db.delete(attendance)
    db.commit()
    return {"status": "deleted", "attendance_id": attendance_id}

@router.post("/bulk-delete")
def bulk_delete_attendance(request: BulkDeleteRequest, db: Session = Depends(get_db), current_member=Depends(get_attendance_delete_manager)):
    if not request.ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
    logger.warning("Bulk deleting attendance records", extra={"type": "attendance_bulk_delete", "ids": request.ids})
    deleted = db.query(models.Attendance).filter(models.Attendance.id.in_(request.ids)).delete(synchronize_session='fetch')
    db.commit()
    return {"status": "deleted", "count": deleted}


@router.get("/stats", response_model=List[schemas.AttendanceStats])
def get_overall_stats(db: Session = Depends(get_db), current_member=Depends(get_attendance_read_manager)):
    members = db.query(models.Member).all()
    attendance = db.query(models.Attendance).all()
    sessions = {s.id: s for s in db.query(models.Session).all()}

    stats = []
    for member in members:
        member_attendance = [a for a in attendance if a.member_id == member.id]
        total = len(member_attendance)
        prompt = 0
        late = 0

        for a in member_attendance:
            session = sessions.get(a.session_id)
            if session and a.timestamp <= session.start_time:
                prompt += 1
            else:
                late += 1

        prompt_rate = (prompt / total * 100) if total > 0 else 0

        stats.append({
            "member_id": member.id,
            "name": member.full_name,
            "total_sessions": total,
            "prompt_count": prompt,
            "late_count": late,
            "prompt_rate": round(prompt_rate, 2)
        })

    # Rank by prompt_rate
    stats.sort(key=lambda x: x["prompt_rate"], reverse=True)
    return stats
