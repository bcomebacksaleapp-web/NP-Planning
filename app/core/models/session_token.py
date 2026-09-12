import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow


class SessionToken(Base):
    """A real, server-verified session -- token_hash is stored, never the raw token (same
    principle as password hashing: if this table leaked, the hashes alone couldn't be used to
    impersonate anyone). Opaque and DB-backed rather than a JWT, since revocation (`revoked_at`)
    is then a simple row update instead of needing a blocklist alongside a stateless token.
    """

    __tablename__ = "session_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
