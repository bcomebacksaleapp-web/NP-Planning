import pytest

from app.core.models.party import Customer, Site
from app.domain.project_lifecycle import transition_project
from app.domain.projects import create_project
from app.domain.state_machine import InvalidTransitionError


def _make_project(session):
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    return create_project(session, site.id, {"name": "v1"})


def test_new_project_starts_discovered(session):
    project = _make_project(session)
    assert project.state == "DISCOVERED"


def test_can_advance_one_step_at_a_time(session):
    project = _make_project(session)
    transition_project(session, project, "QUALIFIED")
    session.commit()
    assert project.state == "QUALIFIED"

    transition_project(session, project, "SURVEY_REQUIRED")
    session.commit()
    assert project.state == "SURVEY_REQUIRED"


def test_cannot_skip_states(session):
    project = _make_project(session)
    with pytest.raises(InvalidTransitionError):
        transition_project(session, project, "FINAL_QUOTE")
    assert project.state == "DISCOVERED"  # unchanged after the failed attempt


def test_cannot_go_backwards(session):
    project = _make_project(session)
    transition_project(session, project, "QUALIFIED")
    session.commit()

    with pytest.raises(InvalidTransitionError):
        transition_project(session, project, "DISCOVERED")
    assert project.state == "QUALIFIED"


def test_full_lifecycle_reaches_the_final_state(session):
    project = _make_project(session)
    remaining_states = [
        "QUALIFIED", "SURVEY_REQUIRED", "SURVEYED", "CONFIGURED", "ESTIMATED",
        "BUDGETARY_QUOTE", "FINAL_QUOTE", "CONFIRMED", "PROCUREMENT_READY", "IN_PROGRESS",
        "HANDOVER", "KNOWLEDGE_HARVEST", "LIFECYCLE",
    ]
    for state in remaining_states:
        transition_project(session, project, state)
    session.commit()
    assert project.state == "LIFECYCLE"
