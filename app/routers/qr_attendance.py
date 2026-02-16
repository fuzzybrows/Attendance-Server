"""
QR code attendance endpoints.
Generates short-lived tokens for session QR codes and verifies them
when members scan and open the link.
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import timedelta
import models, schemas
from database import get_db
from auth import create_access_token, SECRET_KEY, ALGORITHM, get_current_user
from jose import JWTError, jwt
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/attendance/qr",
    tags=["qr-attendance"],
)

QR_TOKEN_EXPIRE_SECONDS = 30


@router.get("/token/{session_id}", response_model=schemas.QRTokenResponse)
def generate_qr_token(session_id: int, db: Session = Depends(get_db), _current_user: str = Depends(get_current_user)):
    """Generate a short-lived token for QR attendance."""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        logger.warning("QR Token gen failed - Session not found", extra={"type": "qr_token_gen_failed", "session_id": session_id, "reason": "session_not_found"})
        raise HTTPException(status_code=404, detail="Session not found")
    
    logger.debug("Generating QR token", extra={"type": "qr_token_gen", "session_id": session_id})

    token = create_access_token(
        data={"qr_session_id": session_id, "type": "qr_attendance"},
        expires_delta=timedelta(seconds=QR_TOKEN_EXPIRE_SECONDS)
    )
    return {"token": token, "expires_in": QR_TOKEN_EXPIRE_SECONDS}


@router.post("/mark", response_model=schemas.QRMarkResponse)
def mark_qr_attendance(
    session_id: int,
    qr_token: str,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Mark attendance via QR code.
    Requires both the QR token (from scan) and the user's auth token (from login).
    """
    # 1. Verify the QR token
    try:
        payload = jwt.decode(qr_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "qr_attendance":
            logger.warning("Invalid QR token type scanned", extra={"type": "qr_scan_invalid_token", "token_type": payload.get("type")})
            raise HTTPException(status_code=400, detail="Invalid QR token type")
        if payload.get("qr_session_id") != session_id:
            logger.warning("QR token mismatch", extra={"type": "qr_scan_mismatch", "token_session_id": payload.get('qr_session_id'), "current_session_id": session_id})
            raise HTTPException(status_code=400, detail="QR token does not match session")
    except JWTError:
        logger.warning("Expired or invalid QR token scanned", extra={"type": "qr_scan_error", "reason": "jwt_error"})
        raise HTTPException(status_code=401, detail="QR code has expired. Please scan again.")

    # 2. Verify the user's auth token
    try:
        auth_token = authorization.replace("Bearer ", "")
        user_payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = user_payload.get("sub")
        if not user_email:
            raise HTTPException(status_code=401, detail="Invalid auth token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Please log in first")

    # 3. Check member exists
    member = db.query(models.Member).filter(models.Member.email == user_email).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # 4. Check session exists
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 5. Check duplicate
    existing = db.query(models.Attendance).filter(
        models.Attendance.member_id == member.id,
        models.Attendance.session_id == session_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Attendance already marked for this session")

    # 6. Mark attendance
    db_attendance = models.Attendance(
        member_id=member.id,
        session_id=session_id,
        latitude=None,
        longitude=None,
        submission_type="qr",
        marked_by_id=None
    )
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)

    logger.info("QR Attendance marked", extra={"type": "qr_attendance_success", "member_id": member.id, "session_id": session_id})
    return {
        "status": "success",
        "message": f"Attendance marked for {member.first_name} {member.last_name}",
        "member_name": member.full_name,
        "attendance_id": db_attendance.id
    }
