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


@pytest.fixture()
def client(session):
    """A FastAPI TestClient wired to the same isolated in-memory SQLite `session` as everything
    else -- without this override, API tests would hit app.core.db.get_db's real engine, i.e.
    the actual dev Postgres database (see .env), which is exactly the kind of test/production
    data mixing the rest of this suite has been careful to avoid throughout."""
    from fastapi.testclient import TestClient

    from app.core.db import get_db
    from app.main import app

    def _override_get_db():
        yield session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
