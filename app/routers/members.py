from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import get_db
from auth import get_password_hash
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/members",
    tags=["members"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.Member)
def create_member(member: schemas.MemberCreate, db: Session = Depends(get_db)):
    logger.info("Creating member", extra={"type": "member_create_attempt", "email": member.email})
    # Check if already exists
    existing = db.query(models.Member).filter(models.Member.email == member.email).first()
    if existing:
        logger.warning("Registration failed - Email exists", extra={"type": "member_create_failed", "email": member.email, "reason": "duplicate_email"})
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Look up default permission object
    default_perm = db.query(models.Permission).filter_by(name="member").first()
    
    db_member = models.Member(
        first_name=member.first_name,
        last_name=member.last_name,
        email=member.email,
        phone_number=member.phone_number,
        password_hash=get_password_hash(member.password),
        nfc_id=member.nfc_id,
        roles=[],
        permissions=[default_perm] if default_perm else [],
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    logger.info("Member created successfully", extra={"type": "member_create_success", "member_id": db_member.id, "email": db_member.email})
    return db_member

@router.get("/", response_model=List[schemas.Member])
def read_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    members = db.query(models.Member).offset(skip).limit(limit).all()
    return members

@router.get("/{member_id}", response_model=schemas.Member)
def read_member(member_id: int, db: Session = Depends(get_db)):
    logger.info("Fetching member details", extra={"type": "member_read_attempt", "member_id": member_id})
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if db_member is None:
        logger.warning("Member not found", extra={"type": "member_read_failed", "member_id": member_id})
        raise HTTPException(status_code=404, detail="Member not found")
    return db_member

@router.put("/{member_id}", response_model=schemas.Member)
def update_member(member_id: int, member_update: schemas.MemberUpdate, db: Session = Depends(get_db)):
    logger.info("Updating member", extra={"type": "member_update", "member_id": member_id})
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    update_data = member_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_member, key, value)
    
    # Update logic for name removed as name is dynamic
    
    db.commit()
    db.refresh(db_member)
    return db_member
