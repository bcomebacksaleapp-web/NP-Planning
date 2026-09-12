# NP Planning

Specialty Contractor Operating System — canonical business platform (Customer / Agent / Business
modes on one shared data layer). See project conversation history for the full Master Blueprint V1.

## Status

**Phase 0 (platform kernel) complete — Sprints 0.1 through 0.8.** No business features yet (that's
Phase 1: Canopy end-to-end) — this phase exists purely to prove the data/migration foundation is
safe before anything real is built on top of it. What's here:

- **Migration pipeline** (0.1): Alembic, every migration reversible, enforced in CI.
- **Core identity/party entities** (0.2): `User`/`Role`/`Permission` (RBAC skeleton, six roles
  seeded), `Customer`/`Site`.
- **Revision pattern** (0.3): current row + append-only revision table (`Project`/
  `ProjectRevision`). Restore always creates a new revision, never rewrites history.
- **Archive framework** (0.4): soft-delete via `archived_at`, never hard-delete, no cascade.
- **Event log + calculation lineage + Time Travel** (0.5): one append-only `Event` table doubling
  as both audit trail and event stream; `make_derived_value()` for engine-versioned calculated
  values; `revision_as_of()` for "what was known as of date X".
- **Authorization check** (0.6): `has_permission()` domain logic only — not wired into HTTP
  request handling yet, since there's no real endpoint to protect and no real auth infrastructure.
- **Feature flags** (0.7): fail-closed on an unknown key.
- **Generic state machine** (0.8): reusable transition-graph engine, wired to `Project`'s 14-state
  lifecycle (Part 23).

All of the Blueprint's own Phase 0 acceptance criteria pass (see `tests/`): create a record, migrate
the schema, read it back, restore an old revision as a new one, archive and recover a record,
preserve a historical calculation while recomputing it separately with a newer engine version.

Two dialect-portability bugs were found and fixed by actually testing every migration against both
SQLite (fast, CI) and real Postgres (the target dialect), not just one — see git log for both.

## Layout

```
app/
  core/     settings, DB engine, ORM models (models/identity.py, party.py, project.py, event.py,
            feature_flag.py)
  domain/   business engine -- revisioning, archiving, events, calculations, time_travel,
            authorization, feature_flags, state_machine, project_lifecycle, projects
  api/      presentation layer (empty -- no real endpoints until Phase 1)
  main.py   FastAPI app (currently: GET /health only)
migrations/ Alembic migration scripts (8, baseline through project lifecycle state)
tests/      37 tests: models, revisioning, archiving, events, calculations, time travel,
            authorization, feature flags, state machine, project lifecycle, migrations, health
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
