import pytest

from app.core.models.critical_spec import CriticalSpec
from app.core.models.event import Event
from app.core.models.party import Customer, Site
from app.domain.critical_specs import create_critical_spec, transition_critical_spec
from app.domain.projects import create_project
from app.domain.state_machine import InvalidTransitionError


def _make_spec(session) -> CriticalSpec:
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    project = create_project(session, site.id, {})
    return create_critical_spec(session, project.id, "roof_material_model", "TN Polycarbonate, 10mm twin-wall")


def test_create_critical_spec_records_an_event(session):
    spec = _make_spec(session)
    session.commit()

    events = session.query(Event).filter_by(entity_type="critical_spec", entity_id=spec.id).all()
    assert len(events) == 1
    assert events[0].event_type == "created"


def test_new_spec_starts_in_discussion(session):
    spec = _make_spec(session)
    assert spec.state == "DISCUSSION"


def test_can_advance_through_the_full_chain(session):
    spec = _make_spec(session)
    transition_critical_spec(session, spec, "PROPOSED")
    session.commit()
    assert spec.state == "PROPOSED"

    transition_critical_spec(session, spec, "CONFIRMED", confirmed_by="Estimator J.")
    session.commit()
    assert spec.state == "CONFIRMED"
    assert spec.confirmed_by == "Estimator J."
    assert spec.confirmed_at is not None


def test_cannot_skip_from_discussion_to_confirmed(session):
    """C5: no critical spec without confirmation -- and confirmation can't be shortcut past
    Proposed."""
    spec = _make_spec(session)
    with pytest.raises(InvalidTransitionError):
        transition_critical_spec(session, spec, "CONFIRMED")
    assert spec.state == "DISCUSSION"
    assert spec.confirmed_at is None


def test_confirming_without_reaching_proposed_first_leaves_confirmed_fields_untouched(session):
    spec = _make_spec(session)
    with pytest.raises(InvalidTransitionError):
        transition_critical_spec(session, spec, "CONFIRMED", confirmed_by="Nobody")
    assert spec.confirmed_by is None
