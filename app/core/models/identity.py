import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, utcnow

# Fixed action-level vocabulary from the platform's Role/Permission model (AI may READ/SUGGEST/
# DRAFT; consequential COMMIT actions require human authorization -- this must never be silently
# bypassed). native_enum=False renders as a portable CHECK constraint instead of a Postgres native
# ENUM type, so extending this list later is a normal migration instead of an ALTER TYPE dance.
ACTION_LEVELS = ("READ", "SUGGEST", "DRAFT", "COMMIT")
# create_constraint=True because SQLAlchemy 1.4+ defaults it to False even for
# native_enum=False -- without it, invalid values pass straight through to the DB unchecked.
ActionLevel = Enum(*ACTION_LEVELS, name="action_level", native_enum=False, create_constraint=True)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Plain string, not a Python/DB enum -- roles are meant to be admin-manageable over time.
    # Seeded with the initial six (CUSTOMER, SITE_ENGINEER, ESTIMATOR, PM, MANAGEMENT,
    # OWNER_ADMIN) via a data migration, but the set is not meant to be hard-coded forever.
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    permissions: Mapped[list["Permission"]] = relationship(
        secondary="role_permissions", back_populates="roles"
    )
    users: Mapped[list["User"]] = relationship(back_populates="role")


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("resource", "action_level", name="uq_permission_resource_action"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # e.g. resource="quote", action_level="COMMIT" -- "who may commit a quote"
    resource: Mapped[str] = mapped_column(String(64), nullable=False)
    action_level: Mapped[str] = mapped_column(ActionLevel, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    roles: Mapped[list["Role"]] = relationship(secondary="role_permissions", back_populates="permissions")


class RolePermission(Base):
    """Join table. A plain association table (no extra columns yet), modeled as its own class
    rather than a bare Table so it's easy to attach columns (e.g. granted_by, granted_at) later
    without a breaking migration."""

    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("permissions.id"), primary_key=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    # Archive, never hard-delete, per platform Law 5 -- NULL means active/not archived.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    role: Mapped["Role"] = relationship(back_populates="users")
