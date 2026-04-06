import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.settings import settings
from app.core.database import get_db
from app.models import Member

# JWT Configuration from settings
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Validate JWT and return the user's email (sub claim)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception
        return sub
    except JWTError:
        raise credentials_exception

def get_current_active_member(
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Member:
    """
    Fetch the full Member object for the current authenticated user.
    """
    member = db.query(Member).filter(Member.email == current_user_email).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member

def _has_any_permission(member: Member, required_perms: List[str]) -> bool:
    """Helper to check if a member has 'admin' or any of the required permissions."""
    return any(p.name in (["admin"] + required_perms) for p in member.permissions)

def get_admin_member(
    member: Member = Depends(get_current_active_member)
) -> Member:
    """Dependency to ensure the user has admin privileges."""
    if not _has_any_permission(member, []): # Only admin
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return member

def get_schedule_read_manager(member: Member = Depends(get_current_active_member)) -> Member:
    """Permission to read the complete schedule/availability matrix."""
    if not _has_any_permission(member, ["schedule_read"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Schedule Read permission required")
    return member

def get_assignments_edit_manager(member: Member = Depends(get_current_active_member)) -> Member:
    """Permission to save or modify draft schedule assignments."""
    if not _has_any_permission(member, ["assignments_edit"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Assignments Edit permission required")
    return member

# Granular Session Permissions
def get_sessions_read_manager(member: Member = Depends(get_current_active_member)) -> Member:
    if not _has_any_permission(member, ["sessions_read"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sessions Read permission required")
    return member

def get_sessions_create_manager(member: Member = Depends(get_current_active_member)) -> Member:
    if not _has_any_permission(member, ["sessions_create"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sessions Create permission required")
    return member

def get_sessions_edit_manager(member: Member = Depends(get_current_active_member)) -> Member:
    if not _has_any_permission(member, ["sessions_edit"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sessions Edit permission required")
    return member

def get_sessions_delete_manager(member: Member = Depends(get_current_active_member)) -> Member:
    if not _has_any_permission(member, ["sessions_delete"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sessions Delete permission required")
    return member

# Granular Attendance Permissions
def get_attendance_read_manager(member: Member = Depends(get_current_active_member)) -> Member:
    if not _has_any_permission(member, ["attendance_read"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Attendance Read permission required")
    return member

def get_attendance_write_manager(member: Member = Depends(get_current_active_member)) -> Member:
    if not _has_any_permission(member, ["attendance_write"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Attendance Write permission required")
    return member

def get_attendance_delete_manager(member: Member = Depends(get_current_active_member)) -> Member:
    if not _has_any_permission(member, ["attendance_delete"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Attendance Delete permission required")
    return member

# Granular Member Permissions
def get_members_read_manager(member: Member = Depends(get_current_active_member)) -> Member:
    if not _has_any_permission(member, ["members_read"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Members Read permission required")
    return member

def get_members_create_manager(member: Member = Depends(get_current_active_member)) -> Member:
    if not _has_any_permission(member, ["members_create"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Members Create permission required")
    return member

def get_members_edit_manager(member: Member = Depends(get_current_active_member)) -> Member:
    if not _has_any_permission(member, ["members_edit"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Members Edit permission required")
    return member

def get_members_delete_manager(member: Member = Depends(get_current_active_member)) -> Member:
    if not _has_any_permission(member, ["members_delete"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Members Delete permission required")
    return member

# Granular Scheduling Permissions
def get_templates_manager(member: Member = Depends(get_current_active_member)) -> Member:
    if not _has_any_permission(member, ["templates_manage"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Templates Manage permission required")
    return member

def get_schedule_generate_manager(member: Member = Depends(get_current_active_member)) -> Member:
    if not _has_any_permission(member, ["schedule_generate"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Schedule Generate permission required")
    return member

def get_schedule_export_manager(member: Member = Depends(get_current_active_member)) -> Member:
    if not _has_any_permission(member, ["schedule_export"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Schedule Export permission required")
    return member
