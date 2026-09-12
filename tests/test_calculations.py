from datetime import datetime, timezone

from app.core.models.party import Customer, Site
from app.core.models.project import ProjectRevision
from app.domain.calculations import make_derived_value
from app.domain.projects import create_project, update_project


def test_make_derived_value_wraps_engine_version_and_inputs():
    result = make_derived_value("pricing-v1", datetime(2026, 3, 15, tzinfo=timezone.utc), total=500_000)
    assert result["engine_version"] == "pricing-v1"
    assert result["values"] == {"total": 500_000}
    assert result["calculated_at"] == "2026-03-15T00:00:00+00:00"


def test_recalculation_with_new_engine_version_does_not_overwrite_historical_value(session):
    """Blueprint Part 8, verbatim: Historical Quote 500,000 using Pricing Engine v1; current
    recalculation 535,000 using Pricing Engine v3. Both values remain visible and distinct --
    this is Law 8 riding on top of the Sprint 0.3 revision pattern plus this lineage wrapper."""
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()

    historical = make_derived_value("pricing-v1", datetime(2026, 1, 1, tzinfo=timezone.utc), total=500_000)
    project = create_project(session, site.id, {"quote": historical})

    recalculated = make_derived_value("pricing-v3", datetime(2026, 6, 1, tzinfo=timezone.utc), total=535_000)
    update_project(session, project, {"quote": recalculated})
    session.commit()

    revisions = (
        session.query(ProjectRevision)
        .filter_by(project_id=project.id)
        .order_by(ProjectRevision.revision_number)
        .all()
    )
    assert revisions[0].data["quote"]["engine_version"] == "pricing-v1"
    assert revisions[0].data["quote"]["values"]["total"] == 500_000
    assert revisions[1].data["quote"]["engine_version"] == "pricing-v3"
    assert revisions[1].data["quote"]["values"]["total"] == 535_000
