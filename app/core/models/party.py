import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, utcnow

# Site types (Blueprint Part 15): HOME / OFFICE / FACTORY is the platform's foundational
# vocabulary for asset types, not an incidental detail -- but native_enum=False still keeps
# extending it a normal migration rather than an ALTER TYPE. create_constraint=True because
# SQLAlchemy 1.4+ defaults it to False even for native_enum=False (see identity.py's ActionLevel).
SITE_TYPES = ("HOME", "OFFICE", "FACTORY")
SiteType = Enum(*SITE_TYPES, name="site_type", native_enum=False, create_constraint=True)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Archive, never hard-delete, per platform Law 5 -- NULL means active/not archived.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sites: Mapped[list["Site"]] = relationship(back_populates="customer")


class Site(Base):
    """The long-lived parent entity per Blueprint Part 15: a Project may close: a Site does not.
    Building / Area / Zone / System / Asset are deferred -- not needed until a phase that
    actually uses them (Part 25: don't build ahead of the vertical slice that needs it)."""

    __tablename__ = "sites"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    site_type: Mapped[str] = mapped_column(SiteType, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="sites")
