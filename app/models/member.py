"""Role, Permission, and Member ORM models."""
from datetime import date
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.associations import member_roles, member_permissions


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    display_order = Column(Integer, nullable=True, comment="Display order for assignable roles. If set, the role is assignable in session scheduling.")

    # Self-referential: on Sundays, members filling this role must ALSO hold the qualifier role.
    # Null means no Sunday restriction. Controlled by ENABLE_SUNDAY_POOL_FILTER setting.
    sunday_qualifier_id = Column(
        Integer,
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to another Role. If set, members must also hold that role to fill this slot on Sundays."
    )
    sunday_qualifier_role = relationship(
        "Role",
        foreign_keys=[sunday_qualifier_id],
        remote_side="Role.id",
        uselist=False,
    )

    @property
    def is_assignable(self):
        return self.display_order is not None


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)


class Member(Base):
    __tablename__ = "members"

    # ── Columns ──
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=True)
    nfc_id = Column(String, unique=True, index=True, nullable=True)
    email_verified = Column(Boolean, default=False)
    phone_number_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    sync_token = Column(String, unique=True, index=True, nullable=True)
    google_refresh_token = Column(String, nullable=True)
    preferred_displayed_firstname = Column(String, nullable=True)

    # Profile fields
    birth_month = Column(Integer, nullable=True)
    birth_day = Column(Integer, nullable=True)
    birth_year = Column(Integer, nullable=True)
    tshirt_size = Column(String, nullable=True)
    address_street = Column(String, nullable=True)
    address_city = Column(String, nullable=True)
    address_state = Column(String, nullable=True)
    address_zip = Column(String, nullable=True)

    # ── Relationships ──
    roles = relationship("Role", secondary=member_roles, backref="members")
    permissions = relationship("Permission", secondary=member_permissions, backref="members")
    attendance = relationship("Attendance", back_populates="member", foreign_keys="[Attendance.member_id]")

    # ── Properties ──
    @property
    def display_first_name(self):
        """Return preferred display name if set, otherwise fall back to first_name."""
        return self.preferred_displayed_firstname or self.first_name

    @property
    def full_name(self):
        return f"{self.display_first_name} {self.last_name}"

    @property
    def date_of_birth(self):
        """Return a date object if month and day are set, using year if available."""
        if self.birth_month and self.birth_day:
            year = self.birth_year or 1900  # fallback year when not provided
            try:
                return date(year, self.birth_month, self.birth_day)
            except ValueError:
                return None
        return None
