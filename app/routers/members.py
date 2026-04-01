from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from core.database import get_db
from core.auth import get_password_hash, get_current_user, get_admin_member, get_current_active_member
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/members",
    tags=["members"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.Member)
def create_member(member: schemas.MemberCreate, db: Session = Depends(get_db), current_member=Depends(get_admin_member)):
    logger.info("Creating member", extra={"type": "member_create_attempt", "email": member.email, "admin": current_member.email})
    # Check if already exists
    existing = db.query(models.Member).filter(models.Member.email == member.email).first()
    if existing:
        logger.warning("Registration failed - Email exists", extra={"type": "member_create_failed", "email": member.email, "reason": "duplicate_email"})
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Look up permissions
    db_perms = []
    if member.permissions:
        db_perms = db.query(models.Permission).filter(models.Permission.name.in_(member.permissions)).all()
    else:
        # Default to 'member' permission if none specified
        default_perm = db.query(models.Permission).filter_by(name="member").first()
        if default_perm:
            db_perms = [default_perm]
            
    # Look up roles
    db_roles = []
    if member.roles:
        db_roles = db.query(models.Role).filter(models.Role.name.in_(member.roles)).all()
            
    db_member = models.Member(
        first_name=member.first_name,
        last_name=member.last_name,
        email=member.email,
        phone_number=member.phone_number,
        password_hash=get_password_hash(member.password),
        nfc_id=member.nfc_id,
        roles=db_roles,
        permissions=db_perms,
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    logger.info("Member created successfully", extra={"type": "member_create_success", "member_id": db_member.id, "email": db_member.email})
    return db_member

@router.get("/metadata", response_model=schemas.MemberMetadata)
def get_member_metadata(db: Session = Depends(get_db)):
    """Returns all available roles and permissions from the database."""
    roles = db.query(models.Role).all()
    permissions = db.query(models.Permission).all()
    return {
        "roles": [r.name for r in roles],
        "permissions": [p.name for p in permissions],
        "choir_roles": [r.name for r in roles if r.is_choir_role]
    }


@router.get("/", response_model=List[schemas.Member])
def read_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_member=Depends(get_current_active_member)):
    # Accessible to all authenticated members (needed for mobile app name resolution)
    # TODO: In future, return a limited "PublicMember" schema for non-admins to hide PII.
    members = db.query(models.Member).offset(skip).limit(limit).all()
    return members

@router.get("/{member_id}", response_model=schemas.Member)
def read_member(member_id: int, db: Session = Depends(get_db), _current_user: str = Depends(get_current_user)):
    logger.info("Fetching member details", extra={"type": "member_read_attempt", "member_id": member_id})
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if db_member is None:
        logger.warning("Member not found", extra={"type": "member_read_failed", "member_id": member_id})
        raise HTTPException(status_code=404, detail="Member not found")
    return db_member

@router.put("/{member_id}", response_model=schemas.Member)
def update_member(member_id: int, member_update: schemas.MemberUpdate, db: Session = Depends(get_db), current_member=Depends(get_admin_member)):
    logger.info("Updating member", extra={"type": "member_update", "member_id": member_id, "admin": current_member.email})
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    update_data = member_update.model_dump(exclude_unset=True)
    
    # Handle M2M relationships separately
    if "roles" in update_data:
        role_names = update_data.pop("roles")
        db_member.roles = db.query(models.Role).filter(models.Role.name.in_(role_names)).all()
    
    if "permissions" in update_data:
        perm_names = update_data.pop("permissions")
        db_member.permissions = db.query(models.Permission).filter(models.Permission.name.in_(perm_names)).all()
    
    # Handle remaining scalar fields
    for key, value in update_data.items():
        setattr(db_member, key, value)
    
    db.commit()
    db.refresh(db_member)
    return db_member
