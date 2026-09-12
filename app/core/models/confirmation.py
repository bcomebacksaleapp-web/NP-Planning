import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow


class Confirmation(Base):
    """What was actually confirmed (Part 6), captured explicitly rather than inferred from
    Project.state == "CONFIRMED" alone -- a state name says something happened; this record says
    exactly what (which quote, which revision) and who confirmed it.

    `override_reason` captures the "why" half of Law 12's who/why for confirming a quote that
    isn't a clean PASS. Risk / financial-impact / expiry -- the rest of Law 12's override fields
    -- are deliberately not modeled yet; a full Override entity with those fields is future work,
    not something to half-build here.
    """

    __tablename__ = "confirmations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    quote_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quotes.id"), nullable=False)
    confirmed_quote_revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    confirmed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    override_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
