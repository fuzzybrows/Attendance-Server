"""
Models package — re-exports all ORM models and the Base for convenient import.
Usage: `import models` continues to work as before.
"""
import enum
from app.core.database import Base

from app.models.associations import member_roles, member_permissions
from app.models.member import Role, Permission, Member
from app.models.session import Session
from app.models.attendance import Attendance
from app.models.availability import Availability
from app.models.assignment import Assignment
from app.models.day_off import DayOff
from app.models.session_template import SessionTemplate


class SessionStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
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
    "Availability",
    "Assignment",
    "DayOff",
    "SessionTemplate",
]
