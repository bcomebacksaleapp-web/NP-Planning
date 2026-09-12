import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow


class Opportunity(Base):
    """A potential project before it's confirmed as a real Project (Part 26 Phase 1: "Agent:
    lead/site"). Tied to a Site, not directly to a Customer, since a Site must already exist for
    there to be anything concrete to survey/quote against -- Part 15's hierarchy.

    No status enum -- the Blueprint doesn't specify one for Opportunity, unlike Project's fixed
    14-state lifecycle (Part 23). `converted_to_project_id` being set is the one state that
    matters structurally (it graduated into a real Project); everything else (open/lost/stalled)
    is free-text in `description` until a real workflow need defines an actual vocabulary.
    """

    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sites.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    converted_to_project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Archive, never hard-delete, per platform Law 5 -- an opportunity that didn't convert is
    # archived, not deleted, so "we had this lead and it went nowhere" stays in history.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
