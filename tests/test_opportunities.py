from app.core.models.event import Event
from app.core.models.party import Customer, Site
from app.domain.opportunities import convert_to_project, create_opportunity


def _make_site(session) -> Site:
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    return site


def test_create_opportunity_records_an_event(session):
    site = _make_site(session)
    opportunity = create_opportunity(session, site.id, source="website_inquiry")
    session.commit()

    events = session.query(Event).filter_by(entity_type="opportunity", entity_id=opportunity.id).all()
    assert len(events) == 1
    assert events[0].event_type == "created"


def test_convert_to_project_creates_a_real_project_and_links_it_back(session):
    site = _make_site(session)
    opportunity = create_opportunity(session, site.id, source="referral")

    project = convert_to_project(session, opportunity, {"name": "New Canopy"})
    session.commit()

    assert opportunity.converted_to_project_id == project.id
    assert project.site_id == site.id
    assert project.state == "DISCOVERED"


def test_opportunity_is_not_archived_just_because_it_converted(session):
    """Converting is itself a fact worth keeping, not a reason to hide the opportunity."""
    site = _make_site(session)
    opportunity = create_opportunity(session, site.id, source="referral")
    convert_to_project(session, opportunity, {"name": "New Canopy"})
    session.commit()

    assert opportunity.archived_at is None
