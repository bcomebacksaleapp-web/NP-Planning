import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, utcnow


class Supplier(Base):
    """A source of qualified price quotes (Part 13.7: Supplier Intelligence).

    Reliability/quality/defect-history tracking -- also listed in Part 13.7 -- is deliberately
    not modeled yet. Those need a real delivery/observation-tracking workflow this phase doesn't
    have; adding empty placeholder columns now would misrepresent something as tracked when
    nothing actually populates it.
    """

    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    quotes: Mapped[list["SupplierQuote"]] = relationship(back_populates="supplier")


class SupplierQuote(Base):
    """One quoted price from one supplier for one material/spec -- Part 13.7's explicit field
    list: quoted price, actual procurement price, quote date, validity, lock period, lead time,
    actual lead time, MOQ.

    `material_description` is a plain string, not a foreign key into a Material catalog -- there
    is no real Material catalog yet (Part 6 lists one, but populating it needs real SKUs/specs
    this phase doesn't have). Each row is already a point-in-time fact (a quote as given on a
    specific date); a superseding quote is a new row, not an edit to this one, so no revision
    pattern is needed on top of it.
    """

    __tablename__ = "supplier_quotes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    material_description: Mapped[str] = mapped_column(String(255), nullable=False)
    quoted_price: Mapped[float] = mapped_column(Float, nullable=False)
    quote_date: Mapped[date] = mapped_column(Date, nullable=False)
    validity_days: Mapped[int] = mapped_column(Integer, nullable=False)
    lock_days: Mapped[int] = mapped_column(Integer, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    # Filled in later, after the quote is acted on -- quoted vs actual is exactly the
    # distinction Part 13.7 asks for.
    actual_lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_procurement_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    moq: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    supplier: Mapped["Supplier"] = relationship(back_populates="quotes")
