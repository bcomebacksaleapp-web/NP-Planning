import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, utcnow

# Must match app.domain.constitution's GATE_* string literals -- no import here on purpose,
# since the data layer (app.core.models) should not depend on the business layer
# (app.domain), only the reverse. They're kept in sync by convention, the same way
# ProjectState's vocabulary lives with the model despite Part 23 also being domain logic.
GATE_STATUSES = ("PASS", "OVERRIDE_REQUIRED", "BLOCKED")
GateStatus = Enum(*GATE_STATUSES, name="gate_status", native_enum=False, create_constraint=True)


class Quote(Base):
    """The 'current' half of the pattern, same shape as Project and ProductRecipe."""

    __tablename__ = "quotes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    revisions: Mapped[list["QuoteRevision"]] = relationship(back_populates="quote")


class QuoteRevision(Base):
    """Append-only pricing decision snapshot for one revision of a Quote.

    true_cost/selling_price/gm_percent/gate_status are the actual GM30 constitution-gate
    decision (C2) as evaluated when this revision was created (Law 8: calculated values must be
    reproducible and store their basis) -- never recalculated in place afterwards. QuoteLine rows
    are informational line-item detail for this same revision; reconciling exactly how per-line
    pricing rolls up into true_cost is future work once a real cost/recipe engine exists (see
    RecipeVersion's docstring in app.core.models.product for why that's deferred for now).
    """

    __tablename__ = "quote_revisions"
    __table_args__ = (UniqueConstraint("quote_id", "revision_number", name="uq_quote_revision_number"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quotes.id"), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    true_cost: Mapped[float] = mapped_column(Float, nullable=False)
    selling_price: Mapped[float] = mapped_column(Float, nullable=False)
    gm_percent: Mapped[float] = mapped_column(Float, nullable=False)
    gate_status: Mapped[str] = mapped_column(GateStatus, nullable=False)
    gate_note: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    restored_from_revision_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    quote: Mapped["Quote"] = relationship(back_populates="revisions")
    lines: Mapped[list["QuoteLine"]] = relationship(back_populates="quote_revision")


class QuoteLine(Base):
    """Informational line-item detail for exactly one QuoteRevision -- never shared or mutated
    across revisions, same append-only discipline as the revision itself.

    `product_id` is nullable and optional -- a line isn't required to tie back to a catalog
    Product (Part 21). When it does, Business Mode's basic product-performance view
    (app.domain.business_health.product_performance_summary) can use it; when it doesn't, the
    line is just informational detail, same as before this column existed.
    """

    __tablename__ = "quote_lines"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    quote_revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quote_revisions.id"), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(256), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    line_total: Mapped[float] = mapped_column(Float, nullable=False)

    quote_revision: Mapped["QuoteRevision"] = relationship(back_populates="lines")
