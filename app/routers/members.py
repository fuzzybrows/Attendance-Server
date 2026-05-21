from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List
from app.models.member import Member, Permission, Role
from app.schemas.member import Member as MemberSchema, MemberCreate, MemberUpdate, MemberMetadata, PasswordResetRequest, ProfileUpdate, PhoneChangeRequest, PhoneVerifyRequest
from app.core.database import get_db
from app.core.auth import (
    get_password_hash, 
    get_current_user, 
    get_admin_member, 
    get_current_active_member,
    get_members_read_manager,
    get_members_create_manager,
    get_members_edit_manager,
    get_members_delete_manager
)
from app.settings import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/members",
    tags=["members"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=MemberSchema)
def create_member(member: MemberCreate, db: Session = Depends(get_db), current_member=Depends(get_members_create_manager)):
    logger.info("Creating member", extra={"type": "member_create_attempt", "email": member.email, "admin": current_member.email})
    # Check if already exists
    existing = db.query(Member).filter(func.lower(Member.email) == member.email).first()
    if existing:
        logger.warning("Registration failed - Email exists", extra={"type": "member_create_failed", "email": member.email, "reason": "duplicate_email"})
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Look up permissions
    db_perms = []
    if member.permissions:
        db_perms = db.query(Permission).filter(Permission.name.in_(member.permissions)).all()
    else:
        # Default to 'member' permission if none specified
        default_perm = db.query(Permission).filter_by(name="member").first()
        if default_perm:
            db_perms = [default_perm]
            
    # Look up roles
    db_roles = []
    if member.roles:
        db_roles = db.query(Role).filter(Role.name.in_(member.roles)).all()
            
    db_member = Member(
        first_name=member.first_name,
        last_name=member.last_name,
        email=member.email,
        phone_number=member.phone_number,
        password_hash=get_password_hash(member.password),
        nfc_id=member.nfc_id,
        roles=db_roles,
        permissions=db_perms,
        is_active=member.is_active,
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    logger.info("Member created successfully", extra={"type": "member_create_success", "member_id": db_member.id, "email": db_member.email})
    return db_member

@router.get("/metadata", response_model=MemberMetadata)
def get_member_metadata(db: Session = Depends(get_db)):
    """Returns all available roles, permissions, assignable roles, and scheduling feature flags."""
    roles = db.query(Role).all()
    permissions = db.query(Permission).all()
    assignable = db.query(Role).filter(Role.display_order.isnot(None)).order_by(Role.display_order.asc()).all()

    # Always expose qualifier relationships from the DB;
    # the flags tell clients whether to apply them.
    sunday_qualifiers = {
        r.name: r.sunday_qualifier_role.name
        for r in assignable
        if r.sunday_qualifier_role is not None
    }

    return {
        "roles": [r.name for r in roles],
        "permissions": [p.name for p in permissions],
        "assignable_roles": [r.name for r in assignable],
        "sunday_qualifiers": sunday_qualifiers,
        "enable_sunday_pool_filter": settings.enable_sunday_pool_filter,
        "enable_sunday_preview_defaults": settings.enable_sunday_preview_defaults,
    }


@router.get("/me", response_model=MemberSchema)
def get_my_profile(current_member: Member = Depends(get_current_active_member)):
    """Return the current authenticated user's full profile."""
    return current_member

@router.put("/me", response_model=MemberSchema)
def update_my_profile(
    profile_update: ProfileUpdate,
    db: Session = Depends(get_db),
    current_member: Member = Depends(get_current_active_member)
):
    """Update the current user's own profile (non-privileged fields only)."""
    update_data = profile_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_member, key, value)
    db.commit()
    db.refresh(current_member)
    logger.info("Profile updated", extra={"type": "profile_self_update", "member_id": current_member.id})
    return current_member

@router.post("/me/change-phone")
def request_phone_change(
    payload: PhoneChangeRequest,
    db: Session = Depends(get_db),
    current_member: Member = Depends(get_current_active_member)
):
    """Send an OTP to the new phone number for verification."""
    from app.services.verification import send_sms_verification
    new_phone = payload.phone_number.strip()
    if not new_phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
    # Check if phone is already taken by another member
    existing = db.query(Member).filter(
        Member.phone_number == new_phone,
        Member.id != current_member.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already in use")
    send_sms_verification(new_phone)
    logger.info("Phone change OTP sent", extra={"type": "phone_change_otp", "member_id": current_member.id})
    return {"status": "otp_sent", "message": "Verification code sent to the new number"}

@router.post("/me/verify-phone", response_model=MemberSchema)
def verify_phone_change(
    payload: PhoneVerifyRequest,
    db: Session = Depends(get_db),
    current_member: Member = Depends(get_current_active_member)
):
    """Verify the OTP and update the phone number."""
    from app.services.verification import check_verification
    new_phone = payload.phone_number.strip()
    if not check_verification(new_phone, payload.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    current_member.phone_number = new_phone
    current_member.phone_number_verified = True
    db.commit()
    db.refresh(current_member)
    logger.info("Phone number changed", extra={"type": "phone_change_success", "member_id": current_member.id, "new_phone": new_phone})
    return current_member

@router.get("/", response_model=List[MemberSchema])
def read_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_member=Depends(get_members_read_manager)):
    # Accessible to all authenticated members (needed for mobile app name resolution)
    # TODO: In future, return a limited "PublicMember" schema for non-admins to hide PII.
    members = db.query(Member).order_by(Member.first_name, Member.last_name).offset(skip).limit(limit).all()
    return members

@router.get("/{member_id}", response_model=MemberSchema)
def read_member(member_id: int, db: Session = Depends(get_db), current_member=Depends(get_members_read_manager)):
    logger.info("Fetching member details", extra={"type": "member_read_attempt", "member_id": member_id})
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if db_member is None:
        logger.warning("Member not found", extra={"type": "member_read_failed", "member_id": member_id})
        raise HTTPException(status_code=404, detail="Member not found")
    return db_member

@router.put("/{member_id}", response_model=MemberSchema)
def update_member(member_id: int, member_update: MemberUpdate, db: Session = Depends(get_db), current_member=Depends(get_members_edit_manager)):
    logger.info("Updating member", extra={"type": "member_update", "member_id": member_id, "admin": current_member.email})
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    update_data = member_update.model_dump(exclude_unset=True)
    
    # Check email uniqueness if email is being changed
    if "email" in update_data and update_data["email"] != db_member.email:
        existing = db.query(Member).filter(
            func.lower(Member.email) == update_data["email"],
            Member.id != member_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Handle M2M relationships separately
    if "roles" in update_data:
        role_names = update_data.pop("roles")
        db_member.roles = db.query(Role).filter(Role.name.in_(role_names)).all()
    
    if "permissions" in update_data:
        perm_names = update_data.pop("permissions")
        db_member.permissions = db.query(Permission).filter(Permission.name.in_(perm_names)).all()
    
    # Handle remaining scalar fields
    for key, value in update_data.items():
        setattr(db_member, key, value)
    
    db.commit()
    db.refresh(db_member)
    return db_member

@router.delete("/{member_id}")
def delete_member(member_id: int, db: Session = Depends(get_db), current_member=Depends(get_members_delete_manager)):
    logger.info("Deleting member", extra={"type": "member_delete", "member_id": member_id, "admin": current_member.email})
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(db_member)
    db.commit()
    return {"status": "deleted", "member_id": member_id}

@router.post("/{member_id}/reset-password")
def reset_member_password(
    member_id: int, 
    payload: PasswordResetRequest, 
    db: Session = Depends(get_db), 
    current_member=Depends(get_members_edit_manager)
):
    logger.info("Resetting member password", extra={"type": "member_password_reset", "member_id": member_id, "admin": current_member.email})
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    db_member.password_hash = get_password_hash(payload.new_password)
    db.commit()
    db.refresh(db_member)
    return {"status": "success", "message": "Password successfully reset"}
