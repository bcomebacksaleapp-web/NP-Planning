# NP Planning

Specialty Contractor Operating System — canonical business platform (Customer / Agent / Business
modes on one shared data layer). See project conversation history for the full Master Blueprint V1.

## Status

**Sprint 0.1 — repo scaffold + migration pipeline.** No business entities, no auth, no UI beyond a
health check. The only thing this sprint proves is that the migration tool works and every
migration is reversible, before anything depends on it.

## Layout

```
app/
  core/     settings + DB engine (single place the DB URL is configured)
  domain/   business engine (empty until Sprint 0.2+)
  api/      presentation layer (empty until Sprint 0.2+)
  main.py   FastAPI app (currently: GET /health only)
migrations/ Alembic migration scripts
tests/
```

## Local setup

```bash
python -m venv .venv
./.venv/Scripts/activate   # or source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env       # edit DATABASE_URL if you have Postgres running
alembic upgrade head
pytest
```

Without a `DATABASE_URL` set, the app falls back to a local SQLite file — convenient for now, but
**Postgres is the target dialect**. SQLite tolerates schema changes Postgres would reject, so
switch to a real Postgres instance (local install or Docker) before Sprint 0.2 adds tables,
to avoid migrations that pass locally but fail against Postgres.

## Conventions

- Every schema change goes through Alembic — never hand-edit the database.
- Every migration must have a working `downgrade()`. `tests/test_migrations.py` enforces
  upgrade→downgrade round-trips in CI.
- `app/core/db.py` is the only place `DATABASE_URL` is read from; `migrations/env.py` imports
  it rather than duplicating it in `alembic.ini`.
