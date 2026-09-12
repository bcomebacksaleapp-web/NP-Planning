import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, utcnow


class WebsiteBranch(Base):
    """Part 9's Business Git applied to the website: MAIN -> HOME-V2 -> FACTORY-EXPERIMENT ->
    NEW-BRAND, etc. `forked_from_branch_id` records lineage only -- it does not copy pages;
    actually branching a page's content is a WebsitePageRevision-level operation (Phase 4 slice
    boundary: this table proves branches exist and can be named/tracked, not a full diff/merge
    engine, which is real product work for a later slice).
    """

    __tablename__ = "website_branches"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    forked_from_branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("website_branches.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WebsitePage(Base):
    """The 'current' half of the current-row + append-only-revision-table pattern (same shape
    as Project, ProductRecipe, Quote) -- the Nth real consumer of Sprint 0.3's revision pattern.
    """

    __tablename__ = "website_pages"
    __table_args__ = (UniqueConstraint("branch_id", "slug", name="uq_website_page_branch_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("website_branches.id"), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    revisions: Mapped[list["WebsitePageRevision"]] = relationship(back_populates="page")


class WebsitePageRevision(Base):
    """Append-only. A page's widget layout for one revision -- WidgetInstance rows belong to
    exactly one revision, same append-only discipline as QuoteLine belonging to one QuoteRevision.
    """

    __tablename__ = "website_page_revisions"
    __table_args__ = (UniqueConstraint("page_id", "revision_number", name="uq_website_page_revision_number"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    page_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("website_pages.id"), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    restored_from_revision_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    page: Mapped["WebsitePage"] = relationship(back_populates="revisions")
    widgets: Mapped[list["WidgetInstance"]] = relationship(back_populates="page_revision")


class WidgetInstance(Base):
    """A controlled widget placement (Part 10) -- widget_type is free text drawn from the
    Blueprint's own example list (Hero, Service Cards, Product Selector, Estimate CTA, Book
    Survey, FAQ, ...), not a closed enum, since Part 10 gives examples, not an exhaustive set.

    `content_source` is a plain descriptive string (e.g. "product:CANOPY"), never a foreign key
    into a business-data table. That is a deliberate, load-bearing choice, not an oversight: Law
    10 requires that deleting a widget instance must NEVER delete canonical business data, and
    Part 11 requires the presentation layer to never own business data. A real FK would tempt an
    ON DELETE CASCADE (or a future schema change that adds one) to reach into business data from
    a presentation-layer delete -- a soft string reference makes that structurally impossible
    instead of merely a rule someone has to remember. See test_website.py for the test that
    actually proves this end to end (a widget referencing a real Product survives the widget's
    own removal, and so does the Product).
    """

    __tablename__ = "widget_instances"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    page_revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("website_page_revisions.id"), nullable=False)
    widget_type: Mapped[str] = mapped_column(String(64), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    visibility_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_source: Mapped[str | None] = mapped_column(String(256), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    page_revision: Mapped["WebsitePageRevision"] = relationship(back_populates="widgets")
