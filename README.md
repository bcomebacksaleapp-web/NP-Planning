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

**Phase 1 (Canopy end-to-end) — Part 26's own checklist fully covered**, modulo one explicit,
labeled placeholder (see below). Customer: configurator. Agent: lead/site, survey, site knowledge,
canopy recipe, quantity, cost, suppliers, fresh price, GM30, quote, confirmation. Business:
pipeline, GM, site capture, basic product performance. Everything the Blueprint specifies with
exact numbers, worked examples, or explicit field lists is built and tested against that source
text directly:

- **Product/ProductRecipe/RecipeVersion** — versioned recipe container (Part 21), reusing the
  Phase 0 revision pattern as its second real consumer.
- **GM30 pricing + Constitution Gate C2** — `Selling Price = True Cost / 0.70`, verified against
  the Blueprint's own worked example.
- **Quote/QuoteRevision/QuoteLine** — same revision pattern, generalized to a normalized line-item
  collection instead of a JSON blob; every revision stores its real GM30 gate decision.
- **Business Mode read views** — pipeline by state, quote GM summary (current revision only), site
  capture by type.
- **Smart Fresh Price** (Part 17) — median reference, lock-duration-aware procurement selection,
  dispersion detection — tested against the Blueprint's own 98/101/105 and 98/101/145 examples.
- **Supplier/SupplierQuote** (Part 13.7) — quoted vs. actual price/lead time, validity, lock,
  MOQ. Feeds real rows into the Fresh Price functions above.
- **Survey/SurveyObservation** (Part 16, "evidence has boundaries") — every field the Blueprint
  names explicitly; never collapses conflicting observations into one "answer".
- **Constitution gates C1/C2/C5/C6/C7/C9** — stale cost, GM30, critical spec confirmation, price
  lock coverage, project-closed-≠-site-closed, capacity — each verbatim from the Blueprint's band
  definitions or state chains, plus `combine_gate_statuses()`: the actual enforcement of
  "a high score cannot compensate for a hard block" (Part 5), not just a comment saying so.
- **Opportunity** — lead capture, converting into a real Project.
- **Confirmation** (Part 6) — what was actually confirmed, not just a Project state name: which
  quote revision, confirmed by whom. A `BLOCKED` quote can never be confirmed (Part 5: no
  commercial override on a hard block); an `OVERRIDE_REQUIRED` one needs an explicit
  `override_reason` or the call is refused (Law 12: who/why).
- **Canopy configurator, end to end** — `configure_canopy_and_create_quote()` takes customer
  dimensions and a roof-cover choice, derives its unit cost either directly or via real Smart
  Fresh Price supplier-quote selection, and produces real `Project`/`ProjectRevision`/`Quote`/
  `QuoteRevision`/`QuoteLine` rows (each line linked to a real `Product`) with a real, *honest*
  gate decision — combining C2 (GM30) with C3 (quantity basis), so a placeholder-quantity quote
  can never show a clean `PASS` just because its margin happens to clear 30%. Verified by
  re-fetching from the database by id, not just checking a return value — directly proving Phase
  1's own acceptance criterion: "Customer configuration must generate canonical business data,
  not UI-only data."

**Still deliberately not built:**
- **Real canopy quantities.** `app/domain/canopy_recipe.py`'s formula is generic, illustrative
  geometry (`roof_area_m2 = width × length`, a round 5% waste factor) tagged
  `UNVERIFIED_PLACEHOLDER` *inside the stored data itself*, not just in a docstring — the warning
  survives being read out of the database later, and its C3 gate keeps every quote built on it
  honestly flagged until it's replaced. No real canopy BOQ methodology exists anywhere on this
  machine (confirmed by searching every other project). Replace before any real quote is issued.
- **Structural sizing** (column/beam/rafter) — never computed, placeholder or not.
  `structure_sizing_status` is always `"PENDING_ENGINEER_CONFIRMATION"`. Part 22 requires a
  qualified engineer to determine this from geometry + load; Law 13 doesn't relax for a
  "just testing" label.
- **Real supplier pricing data** — the Fresh Price wiring exists; no real `SupplierQuote` rows
  have been entered yet.
- C4/C8/C10 and the full weighted Constitution Health composite (Part 5 Step 3) — not blocked on
  data, but on phase sequencing: Part 26 assigns C8/C10 to Phase 5 and Phase 3 respectively, not
  Phase 1, and the composite needs all ten gates real first.
- Any HTTP endpoint beyond `/health`, and real login/session auth — no real endpoint exists to
  protect yet, and a placeholder auth mechanism would be security theater.
- A real Customer Mode UI — this is all domain-layer logic, proven by tests, not a webpage.

**Phase 2 (Agent Intelligence) — underway**, since Phase 1 is complete against its own checklist:

- **What-if Simulator** (Part 13.8) — pure re-evaluation of the existing GM30/gate logic under a
  hypothetical, tested against the Blueprint's own examples verbatim ("What if material price
  rises 8%?", "What if we discount 5%?").
- **Unknown Radar + Survey Mission** (Part 13.3/13.4) — `KNOWN`/`PARTIAL`/`UNKNOWN` classification
  over `SurveyObservation`'s existing fields, not an invented threshold. `survey_checklist()` takes
  the relevant knowledge types as a caller-supplied list rather than hardcoding which ones matter
  per product.
- **Next Best Action** (Part 13.1) — reacts only to structural facts this system already records
  and has tested (`Quote.gate_status`, `CriticalSpec.state`); has nothing to say about a situation
  not already covered by an existing gate. `allowed_next_action` is capped at `SUGGEST`/`DRAFT`,
  tested explicitly (Law 14: never `COMMIT`-level autonomy).
- **Value of Information** (Part 13.5) is not built — it needs real economic-impact modeling
  (estimating cost/risk exposure of an unknown), which runs into the same real-data wall as the
  Canopy takeoff formula.

**Phase 3 (Business Mode) — underway.** C10 (Healthy Sites) was deferred earlier purely for phase
sequencing (Part 26 assigns it here), not missing data — now in sequence, not ahead of it:

- **Healthy Sites** (C10) — `SiteQualityFlag` with the exact flag types C10 lists (bad payment,
  repeated scope abuse, margin leakage, high dispute, excessive admin burden, unsafe practices,
  poor capacity fit). `is_healthy()` is deliberately binary — no formula for a graded score exists
  in the Blueprint, so none is invented here.
- **Revenue / Revenue Floor** (Part 14.1/14.4) — new-vs-repeat customer revenue split, derived
  entirely from real `Confirmation`/`Quote`/`Site` relations already in the system. Recurring/
  maintenance and expansion (the other two Part 14.4 categories) aren't modeled — no Maintenance/
  Repair entity exists yet to distinguish them from a first-time build.
- **Supplier concentration** (Part 14.9) — per-material quote count, distinct-supplier count, and
  single-largest-supplier share, over Phase 1's existing `SupplierQuote` schema. Returns empty
  until real supplier data exists, same as every Business Mode view before real data was there to
  aggregate.
- **5 Capital, Portfolio Mix beyond type/product, Margin Leakage** are not built — they need real
  historical financials, customer-quality signals, or geographic data this repo doesn't have.
- **Business Time Travel** (Part 14.15) — `quote_gm_summary`/`product_performance_summary`/
  `revenue_summary` all accept an optional `as_of`, reusing Phase 0's `revision_as_of` rather than
  reinventing it. Caught a real bug doing this: the existing `archived_at IS NULL` filters would
  have wrongly excluded a site/quote from a *historical* view if it was archived after the as-of
  date but was still active back then — fixed with an "active as of" helper.

**Phase 4 (Website Studio) — kernel started**, schema-level only, following Part 9/10/11's
architecture rather than business-data specifics:

- **WebsiteBranch** (Part 9's Business Git for the website: MAIN → HOME-V2 → FACTORY-EXPERIMENT).
  Records lineage only — a full diff/merge engine is later work.
- **WebsitePage/WebsitePageRevision** — the Nth real consumer of the current-row +
  append-only-revision pattern.
- **WidgetInstance** — `widget_type` drawn from Part 10's own example list, not a closed enum.
  `content_source` is a plain descriptive string (`"product:CANOPY"`), **deliberately never a
  foreign key** into business data — Law 10 requires that deleting a widget instance can never
  delete canonical business data, and a real FK would tempt a future `ON DELETE CASCADE` to
  violate that structurally. Proven directly: a widget referencing a real `Product` survives the
  widget's own removal, and so does the `Product`.
- Full drag-and-drop editing, publishing workflow, diff/merge, and real widget rendering are not
  built — this is the data model only.

## Layout

```
app/
  core/     settings, DB engine, ORM models (identity, party, project, event, feature_flag,
            product, quote, supplier, survey, opportunity, critical_spec, confirmation,
            site_quality_flag, website)
  domain/   business engine -- revisioning, archiving, events, calculations, time_travel,
            authorization, feature_flags, state_machine, project_lifecycle, projects, recipes,
            pricing, constitution, quotes, fresh_price, suppliers, site_knowledge,
            business_health, opportunities, critical_specs, canopy_recipe, canopy_configurator,
            confirmations, what_if, unknown_radar, next_best_action, site_quality, website
  api/      presentation layer (empty -- no real endpoints until real auth exists)
  main.py   FastAPI app (currently: GET /health only)
migrations/ Alembic migration scripts (19, baseline through Website Studio kernel)
tests/      147 tests across all of the above, all passing against both SQLite (CI) and real
            Postgres (verified manually before every commit -- see git log)
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
