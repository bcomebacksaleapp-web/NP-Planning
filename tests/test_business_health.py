from app.core.models.party import Customer, Site
from app.core.models.project import PROJECT_STATES
from app.domain.archiving import archive
from app.domain.business_health import pipeline_by_state, quote_gm_summary, site_capture_summary
from app.domain.pricing import selling_price_for_gm30
from app.domain.project_lifecycle import transition_project
from app.domain.projects import create_project
from app.domain.quotes import create_quote, update_quote


def _make_site(session, site_type="FACTORY") -> Site:
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type=site_type, name="Site A")
    session.add(site)
    session.flush()
    return site


def _price_for_gm(cost: float, gm_pct: float) -> float:
    return cost / (1 - gm_pct / 100)


def test_pipeline_by_state_includes_every_state_even_at_zero(session):
    counts = pipeline_by_state(session)
    assert set(counts.keys()) == set(PROJECT_STATES)
    assert all(v == 0 for v in counts.values())


def test_pipeline_by_state_counts_projects_correctly(session):
    site = _make_site(session)
    p1 = create_project(session, site.id, {})
    p2 = create_project(session, site.id, {})
    transition_project(session, p2, "QUALIFIED")
    session.commit()

    counts = pipeline_by_state(session)
    assert counts["DISCOVERED"] == 1
    assert counts["QUALIFIED"] == 1
    assert counts["SURVEYED"] == 0


def test_pipeline_by_state_excludes_archived_projects(session):
    site = _make_site(session)
    project = create_project(session, site.id, {})
    archive(session, project)
    session.commit()

    counts = pipeline_by_state(session)
    assert counts["DISCOVERED"] == 0


def test_quote_gm_summary_empty_when_no_quotes(session):
    summary = quote_gm_summary(session)
    assert summary == {"quote_count": 0, "average_gm_percent": None, "gate_status_counts": {}}


def test_quote_gm_summary_uses_current_revision_only(session):
    """A superseded revision's GM must not leak into the average -- Law 4 applied to reporting."""
    site = _make_site(session)
    project = create_project(session, site.id, {})
    cost = 100_000
    quote = create_quote(
        session, project.id, cost, selling_price_for_gm30(cost),
        [{"description": "line", "quantity": 1, "unit_price": selling_price_for_gm30(cost)}],
    )
    # Supersede it with a much worse GM -- only THIS should count, not the original 30%.
    update_quote(
        session, quote, cost, _price_for_gm(cost, 10.0),
        [{"description": "line", "quantity": 1, "unit_price": 1}],
    )
    session.commit()

    summary = quote_gm_summary(session)
    assert summary["quote_count"] == 1
    assert round(summary["average_gm_percent"], 2) == 10.0
    assert summary["gate_status_counts"] == {"BLOCKED": 1}


def test_quote_gm_summary_averages_across_multiple_quotes(session):
    site = _make_site(session)
    project_a = create_project(session, site.id, {})
    project_b = create_project(session, site.id, {})
    cost = 100_000
    create_quote(session, project_a.id, cost, _price_for_gm(cost, 30.0), [{"description": "x", "quantity": 1, "unit_price": 1}])
    create_quote(session, project_b.id, cost, _price_for_gm(cost, 20.0), [{"description": "x", "quantity": 1, "unit_price": 1}])
    session.commit()

    summary = quote_gm_summary(session)
    assert summary["quote_count"] == 2
    assert round(summary["average_gm_percent"], 2) == 25.0
    assert summary["gate_status_counts"] == {"PASS": 1, "OVERRIDE_REQUIRED": 1}


def test_site_capture_summary_counts_by_type_and_excludes_archived(session):
    factory = _make_site(session, "FACTORY")
    home = _make_site(session, "HOME")
    archived_office = _make_site(session, "OFFICE")
    archive(session, archived_office)
    session.commit()

    summary = site_capture_summary(session)
    assert summary["total_sites"] == 2
    assert summary["by_type"]["FACTORY"] == 1
    assert summary["by_type"]["HOME"] == 1
    assert summary["by_type"]["OFFICE"] == 0
