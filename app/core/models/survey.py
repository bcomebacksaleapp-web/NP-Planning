import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, utcnow


class Survey(Base):
    """A formal survey request/visit tied to a Project (Part 23: SURVEY_REQUIRED -> SURVEYED)."""

    __tablename__ = "surveys"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    observations: Mapped[list["SurveyObservation"]] = relationship(back_populates="survey")


class SurveyObservation(Base):
    """Site Intelligence (Part 16): one observation with explicit boundaries on how far it
    applies. This is the schema-level answer to Part 16's own example -- never store "Factory A
    piles = 9m" as a bare universal fact; store "previous pile work near Driver Room observed
    <=9m on Job X, applicability limited to this local area unless verified otherwise" instead.
    Every field below exists because Part 16 names it explicitly (Knowledge Type, Location,
    Description, Original Assumption, Observed/Actual, Source, Date, Confidence, Applicability,
    Evidence, Verified by).

    Attached to a Site directly (not only reachable through a Survey), since knowledge can come
    from a past job's records rather than a current formal survey -- Part 16's own worked
    example is exactly that case (a prior job, not this project's survey).

    `evidence_description` is text, not a file attachment, because there's no Document/
    Attachment infrastructure yet (Part 6 lists one, but file storage isn't built).
    """

    __tablename__ = "survey_observations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sites.id"), nullable=False)
    survey_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("surveys.id"), nullable=True)
    knowledge_type: Mapped[str] = mapped_column(String(64), nullable=False)
    location_description: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    original_assumption: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    observed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(32), nullable=True)
    applicability: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    survey: Mapped["Survey | None"] = relationship(back_populates="observations")
