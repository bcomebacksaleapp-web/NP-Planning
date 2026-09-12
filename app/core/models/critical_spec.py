import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow

# C5, verbatim: "No critical spec without confirmation." State: Discussion -> Proposed ->
# Confirmed. Examples given (material model, color, thickness, finish, dimensions, motor model,
# structural requirement, revision) are examples, not a closed vocabulary -- spec_type stays a
# plain string.
CRITICAL_SPEC_STATES = ("DISCUSSION", "PROPOSED", "CONFIRMED")
CriticalSpecState = Enum(
    *CRITICAL_SPEC_STATES, name="critical_spec_state", native_enum=False, create_constraint=True
)


class CriticalSpec(Base):
    """C5: do not procure/fabricate/install critical custom items using verbal memory only.

    No revision pattern here -- unlike Project/Quote, a CriticalSpec's identity is its current
    state in a one-way confirmation workflow, not a history of alternative values worth
    preserving side by side. If "what did we consider before settling on this" turns out to
    matter later, that's a reason to add one, not to assume it now.
    """

    __tablename__ = "critical_specs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    spec_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(CriticalSpecState, default=CRITICAL_SPEC_STATES[0], nullable=False)
    confirmed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
