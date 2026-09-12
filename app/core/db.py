from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM entities."""


def get_db():
    """FastAPI dependency: one Session per request, always closed afterward regardless of
    whether the request raised."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def utcnow() -> datetime:
    """Client-side timestamp default, deliberately not a DB server_default.

    A server_default like `now()` gets compiled into migration DDL as a dialect-specific
    literal (Postgres' `now()` isn't valid SQLite DDL), which breaks the SQLite-based
    migration smoke test in tests/test_migrations.py. A Python-side default sidesteps that
    entirely and behaves identically across dialects.
    """
    return datetime.now(timezone.utc)
