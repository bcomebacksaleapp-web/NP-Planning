import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, utcnow


class Project(Base):
    """The 'current' half of the current-row + append-only-revision-table pattern (Law 4).

    Project itself carries almost no business fields on purpose -- Phase 1 (Canopy) will add
    them via ProjectRevision.data, not by widening this table. Anything that can change over a
    project's life belongs in a revision, not here.

    Deliberately has no current_revision_id pointer column. A Project <-> ProjectRevision FK in
    both directions is a circular dependency that Alembic autogenerate gets the create-table
    order wrong for, and that SQLite can't fix afterwards (no ALTER TABLE ADD CONSTRAINT for
    foreign keys). "Current revision" is just "the row with the highest revision_number for this
    project_id" -- see app.domain.revisioning.latest_revision -- which also removes an entire
    class of pointer/data drift bugs for free.
    """

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sites.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Archive, never hard-delete, per platform Law 5.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    revisions: Mapped[list["ProjectRevision"]] = relationship(back_populates="project")


class ProjectRevision(Base):
    """Append-only. A row here is never updated or deleted once created.

    Restoring an old revision means creating a NEW row that copies its data (see
    app.domain.projects.restore_project_revision) -- never rewinding revision_number or
    mutating an existing row in place. That's the whole of Law 4.
    """

    __tablename__ = "project_revisions"
    __table_args__ = (UniqueConstraint("project_id", "revision_number", name="uq_project_revision_number"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Free-form for now -- Project's real business fields don't exist until Phase 1 (Canopy).
    # Whatever they turn out to be, they belong in here, not as columns on Project itself.
    # sqlalchemy.JSON (not postgresql.JSONB) deliberately -- stays testable against SQLite too.
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Set only when this revision was created by a restore; records which old revision_number it
    # came from, so Time Travel can show "this is Rev 15, restored from Rev 12" (Blueprint Part 8).
    restored_from_revision_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="revisions")
