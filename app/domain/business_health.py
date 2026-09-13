"""Business Mode read-side views (Part 14). Pure aggregation over whatever canonical data
already exists -- no business formulas invented here, unlike the still-pending Canopy takeoff
math (see app.core.models.product.RecipeVersion's docstring). These only ever read; none of
them write.
"""

from collections import Counter
from datetime import datetime

from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.orm import aliased

from app.core.models.confirmation import Confirmation
from app.core.models.party import SITE_TYPES, Site
from app.core.models.product import Product
from app.core.models.project import PROJECT_STATES, Project
from app.core.models.quote import Quote, QuoteRevision
from app.core.models.site_quality_flag import SiteQualityFlag
from app.core.models.supplier import SupplierQuote


def _active_as_of(model, as_of: datetime | None):
    """A row is "active as of" a point in time when it hadn't been archived yet then -- either
    never archived, or archived after `as_of`. Without the second clause, "View the business as
    of 15 Mar 2026" would incorrectly exclude something that was still active back then but has
    since been archived (Part 8's Time Travel principle applied to these Business Mode views).
    """
    if as_of is None:
        return model.archived_at.is_(None)
    return or_(model.archived_at.is_(None), model.archived_at > as_of)


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


def _current_quote_revisions(session, as_of: datetime | None) -> list[QuoteRevision]:
    """Shared by every view below that needs "each quote's revision, as of a point in time" --
    the latest one that existed by `as_of` (Part 8: never surface a revision created after the
    date being viewed), or simply the current one when as_of is None.

    One query via ROW_NUMBER(), not N+1 (one query per quote via
    app.domain.revisioning.latest_revision/time_travel.revision_as_of, as this used to do).
    Those two helpers stay as they are -- they're the right tool for "this one quote's revision"
    -- this is specifically for "every quote's revision at once", which needs its own query
    shape to avoid looping a per-quote lookup over however many quotes exist.
    """
    row_number = func.row_number().over(
        partition_by=QuoteRevision.quote_id, order_by=QuoteRevision.revision_number.desc()
    ).label("rn")
    filters = [QuoteRevision.quote_id.in_(select(Quote.id).where(_active_as_of(Quote, as_of)))]
    if as_of is not None:
        filters.append(QuoteRevision.created_at <= as_of)

    ranked = select(QuoteRevision, row_number).where(*filters).subquery()
    revision = aliased(QuoteRevision, ranked)
    return list(session.execute(select(revision).where(ranked.c.rn == 1)).scalars())


def quote_gm_summary(session, as_of: datetime | None = None) -> dict:
    """Average GM% and gate-status breakdown across each quote's CURRENT revision only (or, with
    `as_of`, each quote's revision as it stood at that point in time -- Part 14.15's Business
    Time Travel applied to this view).

    An old, superseded revision's GM must never be double-counted into a portfolio-wide average
    -- it's history (Law 4), not current state. Archived quotes are excluded the same way
    pipeline_by_state excludes archived projects, adjusted for `as_of` (see _active_as_of).
    """
    current_revisions = _current_quote_revisions(session, as_of)

    if not current_revisions:
        return {"quote_count": 0, "average_gm_percent": None, "gate_status_counts": {}}

    gate_counts = Counter(rev.gate_status for rev in current_revisions)
    average_gm = sum(rev.gm_percent for rev in current_revisions) / len(current_revisions)
    return {
        "quote_count": len(current_revisions),
        "average_gm_percent": average_gm,
        "gate_status_counts": dict(gate_counts),
    }


def product_performance_summary(session, as_of: datetime | None = None) -> dict:
    """Part 26 Phase 1's "basic product performance": revenue and quote-line count per Product,
    from each quote's CURRENT revision only (or, with `as_of`, as it stood at that point in
    time) -- same "current revision only" discipline as quote_gm_summary, for the same reason.
    Lines with no product_id (informational-only lines, or quotes predating this column) are
    grouped under "unlinked" rather than silently dropped.
    """
    products_by_id = {p.id: p.code for p in session.execute(select(Product)).scalars()}
    current_revisions = _current_quote_revisions(session, as_of)

    revenue_by_product: dict[str, float] = {}
    line_count_by_product: dict[str, int] = {}
    for revision in current_revisions:
        for line in revision.lines:
            key = products_by_id.get(line.product_id, "unlinked") if line.product_id else "unlinked"
            revenue_by_product[key] = revenue_by_product.get(key, 0.0) + line.line_total
            line_count_by_product[key] = line_count_by_product.get(key, 0) + 1

    return {"revenue_by_product": revenue_by_product, "line_count_by_product": line_count_by_product}


def site_capture_summary(session) -> dict:
    """Count of active captured sites, by type (Part 15's HOME/OFFICE/FACTORY vocabulary)."""
    by_type = {site_type: 0 for site_type in SITE_TYPES}
    total = 0
    for site_type in session.execute(select(Site.site_type).where(Site.archived_at.is_(None))).scalars():
        by_type[site_type] += 1
        total += 1
    return {"total_sites": total, "by_type": by_type}


def healthy_sites_summary(session) -> dict:
    """Part 14.1's "Healthy Sites", using C10's binary flag-based definition (see
    app.domain.site_quality.is_healthy) -- not a scored composite, since the Blueprint gives no
    formula for one.

    One query for all sites' active flags, not N+1 (one is_healthy() call per site, as this
    used to do) -- is_healthy() itself is unchanged and still the right tool for "is this one
    site healthy", just not looped here anymore.
    """
    total_sites = session.execute(select(func.count()).select_from(Site).where(Site.archived_at.is_(None))).scalar_one()
    # Joined to Site and filtered by archived_at too -- a flag on an archived site must not
    # count here, or flagged_sites could exceed total_sites (an archived site isn't in that
    # count at all) and healthy_sites would go negative.
    flagged_sites = session.execute(
        select(func.count(func.distinct(SiteQualityFlag.site_id)))
        .join(Site, Site.id == SiteQualityFlag.site_id)
        .where(SiteQualityFlag.resolved_at.is_(None), Site.archived_at.is_(None))
    ).scalar_one()
    return {"total_sites": total_sites, "healthy_sites": total_sites - flagged_sites, "flagged_sites": flagged_sites}


def revenue_summary(session, as_of: datetime | None = None) -> dict:
    """Part 14.1's "Revenue" plus Part 14.4's new-vs-repeat split, derived only from real
    Confirmation + Quote data -- no invented percentages. A customer's SECOND (or later)
    confirmed project counts as repeat business; their first is new acquisition.

    `as_of` (Part 14.15 Business Time Travel): a Confirmation is itself a point-in-time decision
    record, so "revenue as of a date" is simply every confirmation that had happened by then --
    no need for revision_as_of here the way quote_gm_summary needs it, since
    confirmed_quote_revision_number is already fixed at confirmation time and never changes.

    Recurring/maintenance and expansion (the other two Part 14.4 categories) aren't modeled yet
    -- there's no Maintenance/Repair entity to distinguish them from a first-time build.
    """
    query = select(Confirmation).order_by(Confirmation.confirmed_at)
    if as_of is not None:
        query = query.where(Confirmation.confirmed_at <= as_of)
    confirmations = session.execute(query).scalars().all()

    # Three batch queries total, not three PER confirmation (a real N+1 this used to have) --
    # one for every needed QuoteRevision (via a composite-key IN), one for every needed
    # Project, one for every needed Site.
    seen_customer_ids: set = set()
    new_customer_revenue = 0.0
    repeat_customer_revenue = 0.0

    if confirmations:
        revision_keys = [(c.quote_id, c.confirmed_quote_revision_number) for c in confirmations]
        revisions_by_key = {
            (r.quote_id, r.revision_number): r
            for r in session.execute(
                select(QuoteRevision).where(
                    tuple_(QuoteRevision.quote_id, QuoteRevision.revision_number).in_(revision_keys)
                )
            ).scalars()
        }

        project_ids = {c.project_id for c in confirmations}
        projects_by_id = {p.id: p for p in session.execute(select(Project).where(Project.id.in_(project_ids))).scalars()}

        site_ids = {p.site_id for p in projects_by_id.values()}
        sites_by_id = {s.id: s for s in session.execute(select(Site).where(Site.id.in_(site_ids))).scalars()}

        for confirmation in confirmations:
            quote_revision = revisions_by_key[(confirmation.quote_id, confirmation.confirmed_quote_revision_number)]
            project = projects_by_id[confirmation.project_id]
            site = sites_by_id[project.site_id]

            if site.customer_id in seen_customer_ids:
                repeat_customer_revenue += quote_revision.selling_price
            else:
                new_customer_revenue += quote_revision.selling_price
                seen_customer_ids.add(site.customer_id)

    return {
        "total_confirmed_revenue": new_customer_revenue + repeat_customer_revenue,
        "new_customer_revenue": new_customer_revenue,
        "repeat_customer_revenue": repeat_customer_revenue,
    }


def supplier_concentration_summary(session) -> dict:
    """Part 14.9: supplier concentration / single-source risk, per material. The single
    largest supplier's share of quotes for that material is exactly what "concentration risk"
    means -- a high share means the business has few real alternatives if that one supplier
    fails to deliver.

    Reads whatever SupplierQuote rows exist (Part 13.7's schema, Phase 1) -- there is no real
    supplier data entered yet, so in practice this returns an empty dict today, same as every
    other Business Mode view before real data existed to aggregate.
    """
    quotes = session.execute(select(SupplierQuote)).scalars().all()
    counts_by_material: dict[str, Counter] = {}
    for quote in quotes:
        counts_by_material.setdefault(quote.material_description, Counter())[quote.supplier_id] += 1

    result = {}
    for material, counts in counts_by_material.items():
        total = sum(counts.values())
        _, top_count = counts.most_common(1)[0]
        result[material] = {
            "quote_count": total,
            "distinct_suppliers": len(counts),
            "top_supplier_share_percent": top_count / total * 100,
        }
    return result
