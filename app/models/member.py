"""Role, Permission, and Member ORM models."""
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from core.database import Base
from models.associations import member_roles, member_permissions


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    is_choir_role = Column(Boolean, default=False, comment="Flag to identify roles used for choir scheduling slots (e.g. Soprano, Alto).")


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    email = Column(String, unique=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=True)
    nfc_id = Column(String, unique=True, index=True, nullable=True)

    # Relationships
    roles = relationship("Role", secondary=member_roles, backref="members")
    permissions = relationship("Permission", secondary=member_permissions, backref="members")

    email_verified = Column(Boolean, default=False)
    phone_number_verified = Column(Boolean, default=False)

    attendance = relationship("Attendance", back_populates="member", foreign_keys="[Attendance.member_id]")

    sync_token = Column(String, unique=True, index=True, nullable=True)
    google_refresh_token = Column(String, nullable=True)
