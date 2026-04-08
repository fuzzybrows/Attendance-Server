from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Optional
import logging
from app.models.session import Session as SessionModel
from app.models.attendance import Attendance
from app.core.utils import calculate_distance

logger = logging.getLogger(__name__)

def validate_attendance(
    db: Session,
    session: SessionModel,
    member_id: int,
    device_id: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    marked_by_id: Optional[int]
):
    """
    Validates attendance submission against fraud prevention rules:
    1. Device Lock (Anti-Buddy Punching)
    2. Geofencing
    3. Duplicate Attendance
    
    Raises HTTPException if any check fails.
    """
    
    # Determine if this is an admin override (marked by someone other than the member)
    is_self_checkin = (marked_by_id is None) or (marked_by_id == member_id)
    is_admin_override = not is_self_checkin

    # 1. Device Lock Check (Anti-Buddy Punching)
    # Only enforce if self-check-in
    if is_self_checkin and device_id:
        existing_device_usage = db.query(Attendance).filter(
            Attendance.session_id == session.id,
            Attendance.device_id == device_id,
            Attendance.member_id != member_id
        ).first()

        if existing_device_usage:
            logger.warning("Device Lock triggered", extra={
                "type": "fraud_prevented",
                "subtype": "device_lock",
                "device_id": device_id,
                "session_id": session.id
            })
            raise HTTPException(status_code=403, detail="This device has already been used to mark attendance for another member in this session.")

    # 2. Geofence Check – skip for admin overrides
    if not is_admin_override and session.latitude is not None and session.longitude is not None and session.radius:
        if latitude is None or longitude is None:
             raise HTTPException(status_code=403, detail="Location access is required for this session.")
        
        distance = calculate_distance(
            session.latitude, session.longitude,
            latitude, longitude
        )

        if distance > session.radius:
            logger.warning("Geofence blocked", extra={
                "type": "fraud_prevented",
                "subtype": "geofence",
                "distance": distance,
                "radius": session.radius
            })
            raise HTTPException(status_code=403, detail=f"You are too far from the venue ({int(distance)}m). You must be within {session.radius}m.")
    
    if is_admin_override:
        logger.info("Admin override – skipping geofence/device checks", extra={
            "type": "admin_override",
            "marked_by_id": marked_by_id,
            "member_id": member_id,
            "session_id": session.id
        })

    # 3. Duplicate Check
    existing = db.query(Attendance).filter(
        Attendance.member_id == member_id,
        Attendance.session_id == session.id
    ).first()
    
    if existing:
        logger.warning("Duplicate attendance attempt", extra={"type": "attendance_duplicate", "member_id": member_id, "session_id": session.id})
        raise HTTPException(status_code=409, detail="Attendance already marked for this session")
