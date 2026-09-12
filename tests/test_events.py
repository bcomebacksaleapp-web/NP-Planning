from sqlalchemy import select

from app.core.models.event import Event
from app.core.models.party import Customer, Site
from app.domain.archiving import archive
from app.domain.projects import create_project, restore_project_revision, update_project


def _events_for(session, entity_type, entity_id):
    return list(
        session.execute(
            select(Event).where(Event.entity_type == entity_type, Event.entity_id == entity_id)
        ).scalars()
    )


def _make_site(session) -> Site:
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    return site


def test_create_project_records_a_created_event(session):
    site = _make_site(session)
    project = create_project(session, site.id, {"name": "v1"})
    session.commit()

    events = _events_for(session, "project", project.id)
    assert len(events) == 1
    assert events[0].event_type == "created"
    assert events[0].payload == {"revision_number": 1}


def test_update_and_restore_each_record_their_own_event(session):
    site = _make_site(session)
    project = create_project(session, site.id, {"name": "v1"})
    update_project(session, project, {"name": "v2"})
    restore_project_revision(session, project, target_revision_number=1)
    session.commit()

    events = sorted(_events_for(session, "project", project.id), key=lambda e: e.occurred_at)
    assert [e.event_type for e in events] == ["created", "revision_created", "revision_restored"]
    assert events[2].payload == {"revision_number": 3, "restored_from_revision_number": 1}


def test_archive_records_an_event_and_repeated_archive_does_not_double_log(session):
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()

    archive(session, customer)
    archive(session, customer)  # idempotent -- must not log a second event
    session.commit()

    events = _events_for(session, customer.__tablename__, customer.id)
    assert len(events) == 1
    assert events[0].event_type == "archived"
