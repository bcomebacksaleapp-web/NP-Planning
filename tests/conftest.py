import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.db import Base
import app.core.models  # noqa: F401 -- populates Base.metadata


@pytest.fixture()
def session():
    # In-memory SQLite, one connection for the whole test via StaticPool -- otherwise each
    # checkout gets a fresh :memory: database and the schema created below would vanish.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    # SQLite ignores FOREIGN KEY constraints unless explicitly turned on per-connection --
    # without this, FK-violation tests would pass for the wrong reason.
    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
