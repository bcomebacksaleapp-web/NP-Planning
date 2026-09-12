from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Shared declarative base. Sprint 0.1 defines no tables yet -- entities land in Sprint 0.2."""
