from datetime import datetime


def make_derived_value(engine_version: str, calculated_at: datetime, **values) -> dict:
    """Wraps a calculated value with its lineage metadata (Law 8: every calculated value must be
    reproducible and store its calculation/engine version).

    Store the result of this in a revision's `data`, not a bare unwrapped dict -- Phase 1's real
    calculation engines (pricing, GM, capacity) should use this same shape. Combined with the
    revision pattern from Sprint 0.3, it's what makes Blueprint Part 8's example work: "Historical
    Quote 500,000 using Pricing Engine v1" and "current recalculation 535,000 using Pricing Engine
    v3" can both exist, distinct and visible, because recalculating never overwrites the old
    revision -- it creates a new one wrapping the new engine_version.
    """
    return {
        "engine_version": engine_version,
        "calculated_at": calculated_at.isoformat(),
        "values": values,
    }
