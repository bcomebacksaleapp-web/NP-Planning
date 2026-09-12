"""Business Mode read-side views (Part 14). Pure aggregation over whatever canonical data
already exists -- no business formulas invented here, unlike the still-pending Canopy takeoff
math (see app.core.models.product.RecipeVersion's docstring). These only ever read; none of
them write.
"""

from collections import Counter

from sqlalchemy import select

from app.core.models.party import SITE_TYPES, Site
from app.core.models.project import PROJECT_STATES, Project
from app.core.models.quote import Quote, QuoteRevision
from app.domain.revisioning import latest_revision


def pipeline_by_state(session) -> dict[str, int]:
    """Count of active (non-archived) projects per lifecycle state (Part 23). Every state from
    Project's fixed vocabulary is included even at zero, so an empty state doesn't just vanish
    from the view -- a management dashboard should be able to tell "no projects here" from
    "we forgot to query this state".
    """
    counts = {state: 0 for state in PROJECT_STATES}
    for state in session.execute(select(Project.state).where(Project.archived_at.is_(None))).scalars():
        counts[state] += 1
    return counts


def quote_gm_summary(session) -> dict:
    """Average GM% and gate-status breakdown across each quote's CURRENT revision only.

    An old, superseded revision's GM must never be double-counted into a portfolio-wide average
    -- it's history (Law 4), not current state. Archived quotes are excluded the same way
    pipeline_by_state excludes archived projects.
    """
    quote_ids = session.execute(select(Quote.id).where(Quote.archived_at.is_(None))).scalars().all()
    current_revisions = [
        rev
        for rev in (latest_revision(session, QuoteRevision, "quote_id", qid) for qid in quote_ids)
        if rev is not None
    ]

    if not current_revisions:
        return {"quote_count": 0, "average_gm_percent": None, "gate_status_counts": {}}

    gate_counts = Counter(rev.gate_status for rev in current_revisions)
    average_gm = sum(rev.gm_percent for rev in current_revisions) / len(current_revisions)
    return {
        "quote_count": len(current_revisions),
        "average_gm_percent": average_gm,
        "gate_status_counts": dict(gate_counts),
    }


def site_capture_summary(session) -> dict:
    """Count of active captured sites, by type (Part 15's HOME/OFFICE/FACTORY vocabulary)."""
    by_type = {site_type: 0 for site_type in SITE_TYPES}
    total = 0
    for site_type in session.execute(select(Site.site_type).where(Site.archived_at.is_(None))).scalars():
        by_type[site_type] += 1
        total += 1
    return {"total_sites": total, "by_type": by_type}
