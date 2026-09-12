import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow


class Event(Base):
    """Append-only event/audit log. Serves both the general event stream (Time Travel: 'what
    happened and when') and the audit trail (Law: critical actions record who/when/why) for
    Phase 0 -- one table, not two, since nothing yet needs different shapes or retention. Split
    a dedicated AuditLog out later only if a concrete need for that actually shows up (e.g. Law
    12's override fields: risk, financial impact, expiry).

    entity_id is a plain UUID, not a foreign key -- it's polymorphic (entity_type says which
    table it points into), and one column can't carry a FK into N different tables.
    """

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # Nullable -- Phase 0 has no auth wiring yet, so some events are system-initiated (no actor).
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
