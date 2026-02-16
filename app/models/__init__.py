"""
Models package — re-exports all ORM models and the Base for convenient import.
Usage: `import models` continues to work as before.
"""
import enum
from core.database import Base

from models.associations import member_roles, member_permissions
from models.member import Role, Permission, Member
from models.session import Session
from models.attendance import Attendance


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    CONCLUDED = "concluded"
    ARCHIVED = "archived"


__all__ = [
    "Base",
    "SessionStatus",
    "member_roles",
    "member_permissions",
    "Role",
    "Permission",
    "Member",
    "Session",
    "Attendance",
]
