from datetime import datetime, timezone

from app.core.models.party import Customer, Site
from app.core.models.project import Project, ProjectRevision
from app.domain.time_travel import revision_as_of


def test_revision_as_of_returns_only_what_was_known_at_that_time(session):
    """Blueprint Part 8: 'View Factory A as of 15 Mar 2026' must show only information known at
    that time -- never a revision created later."""
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    project = Project(site_id=site.id)
    session.add(project)
    session.flush()

    jan, march, june = (
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    session.add_all(
        [
            ProjectRevision(project_id=project.id, revision_number=1, data={"v": 1}, created_at=jan),
            ProjectRevision(project_id=project.id, revision_number=2, data={"v": 2}, created_at=march),
            ProjectRevision(project_id=project.id, revision_number=3, data={"v": 3}, created_at=june),
        ]
    )
    session.commit()

    before_anything = revision_as_of(
        session, ProjectRevision, "project_id", project.id, datetime(2025, 12, 1, tzinfo=timezone.utc)
    )
    assert before_anything is None

    as_of_feb = revision_as_of(
        session, ProjectRevision, "project_id", project.id, datetime(2026, 2, 1, tzinfo=timezone.utc)
    )
    assert as_of_feb.revision_number == 1  # revision 2 (March) didn't exist yet

    as_of_april = revision_as_of(
        session, ProjectRevision, "project_id", project.id, datetime(2026, 4, 1, tzinfo=timezone.utc)
    )
    assert as_of_april.revision_number == 2

    as_of_now = revision_as_of(
        session, ProjectRevision, "project_id", project.id, datetime(2026, 12, 1, tzinfo=timezone.utc)
    )
    assert as_of_now.revision_number == 3
