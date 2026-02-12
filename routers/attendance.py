from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from pydantic import BaseModel
import models, schemas
from database import get_db
import logging

logger = logging.getLogger(__name__)

class BulkDeleteRequest(BaseModel):
    ids: List[int]

router = APIRouter(
    prefix="/attendance",
    tags=["attendance"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.Attendance)
def mark_attendance(attendance: schemas.AttendanceCreate, db: Session = Depends(get_db)):
    logger.info("Marking attendance", extra={"type": "attendance_mark_attempt", "member_id": attendance.member_id, "session_id": attendance.session_id})
    # Verify member and session exist
    member = db.query(models.Member).filter(models.Member.id == attendance.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    session = db.query(models.Session).filter(models.Session.id == attendance.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check for duplicate attendance
    existing = db.query(models.Attendance).filter(
        models.Attendance.member_id == attendance.member_id,
        models.Attendance.session_id == attendance.session_id
    ).first()
    if existing:
        logger.warning("Duplicate attendance attempt", extra={"type": "attendance_duplicate", "member_id": attendance.member_id, "session_id": attendance.session_id})
        raise HTTPException(status_code=409, detail="Attendance already marked for this session")

    db_attendance = models.Attendance(
        member_id=attendance.member_id,
        session_id=attendance.session_id,
        latitude=attendance.latitude,
        longitude=attendance.longitude,
        submission_type=attendance.submission_type,
        marked_by_id=attendance.marked_by_id
    )
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)
    return db_attendance

@router.get("/session/{session_id}", response_model=List[schemas.Attendance])
def read_attendance(session_id: int, db: Session = Depends(get_db)):
    attendance = db.query(models.Attendance).filter(models.Attendance.session_id == session_id).all()
    attendance = db.query(models.Attendance).filter(models.Attendance.session_id == session_id).all()
    return attendance

@router.get("/member/{member_id}", response_model=List[schemas.AttendanceWithSession])
def get_member_attendance(member_id: int, db: Session = Depends(get_db)):
    attendance = db.query(models.Attendance)\
        .options(joinedload(models.Attendance.session))\
        .filter(models.Attendance.member_id == member_id)\
        .order_by(models.Attendance.timestamp.desc())\
        .all()
    return attendance

@router.delete("/{attendance_id}")
def delete_attendance(attendance_id: int, db: Session = Depends(get_db)):
    attendance = db.query(models.Attendance).filter(models.Attendance.id == attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    db.delete(attendance)
    db.commit()
    return {"status": "deleted", "attendance_id": attendance_id}

@router.post("/bulk-delete")
def bulk_delete_attendance(request: BulkDeleteRequest, db: Session = Depends(get_db)):
    if not request.ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
    logger.warning("Bulk deleting attendance records", extra={"type": "attendance_bulk_delete", "ids": request.ids})
    deleted = db.query(models.Attendance).filter(models.Attendance.id.in_(request.ids)).delete(synchronize_session='fetch')
    db.commit()
    return {"status": "deleted", "count": deleted}


@router.get("/stats")
def get_overall_stats(db: Session = Depends(get_db)):
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
            "name": member.name,
            "total_sessions": total,
            "prompt_count": prompt,
            "late_count": late,
            "prompt_rate": round(prompt_rate, 2)
        })

    # Rank by prompt_rate
    stats.sort(key=lambda x: x["prompt_rate"], reverse=True)
    return stats
