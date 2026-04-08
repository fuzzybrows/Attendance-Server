"""Association tables for many-to-many relationships."""
from sqlalchemy import Table, Column, Integer, ForeignKey
from app.core.database import Base

member_roles = Table(
    'member_roles', Base.metadata,
    Column('member_id', Integer, ForeignKey('members.id')),
    Column('role_id', Integer, ForeignKey('roles.id'))
)

member_permissions = Table(
    'member_permissions', Base.metadata,
    Column('member_id', Integer, ForeignKey('members.id')),
    Column('permission_id', Integer, ForeignKey('permissions.id'))
)
