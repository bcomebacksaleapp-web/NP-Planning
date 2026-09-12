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

PostgreSQL 17 is installed locally (via winget, `postgresql-x64-17` Windows service) with a
dedicated `np_planning` database owned by role `np_planning_app` (not the `postgres` superuser).
Credentials live in `.env` (gitignored, not in this repo).

```bash
python -m venv .venv
./.venv/Scripts/activate   # or source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env       # fill in DATABASE_URL -- ask whoever set up the local Postgres instance
alembic upgrade head
pytest
```

Without a `DATABASE_URL` set, the app falls back to a local SQLite file. `tests/test_migrations.py`
deliberately still uses a throwaway SQLite file for its upgrade/downgrade round-trip (fast, no
dependency on a running Postgres) — that's a smoke test for the migration *tool*, not a substitute
for running real migrations against Postgres before trusting a schema change.

## Conventions

- Every schema change goes through Alembic — never hand-edit the database.
- Every migration must have a working `downgrade()`. `tests/test_migrations.py` enforces
  upgrade→downgrade round-trips in CI.
- `app/core/db.py` is the only place `DATABASE_URL` is read from; `migrations/env.py` imports
  it rather than duplicating it in `alembic.ini`.
