import pytest

from app.core.models.event import Event
from app.core.models.party import Customer, Site
from app.domain.confirmations import (
    ConfirmationBlockedError,
    ConfirmationRequiresOverrideReasonError,
    confirm_project,
)
from app.domain.pricing import selling_price_for_gm30
from app.domain.projects import create_project
from app.domain.quotes import create_quote


def _make_project_and_quote(session, gm_percent: float):
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    project = create_project(session, site.id, {})

    cost = 100_000
    price = cost / (1 - gm_percent / 100)
    quote = create_quote(session, project.id, cost, price, [{"description": "x", "quantity": 1, "unit_price": price}])
    return project, quote


def test_confirming_a_passing_quote_walks_project_to_confirmed(session):
    project, quote = _make_project_and_quote(session, gm_percent=35.0)
    confirmation = confirm_project(session, project, quote, confirmed_by="Estimator J.")
    session.commit()

    assert project.state == "CONFIRMED"
    assert confirmation.confirmed_by == "Estimator J."
    assert confirmation.confirmed_quote_revision_number == 1
    assert confirmation.override_reason is None


def test_confirming_a_blocked_quote_is_refused_outright(session):
    """Part 5: no commercial override on a hard block."""
    project, quote = _make_project_and_quote(session, gm_percent=5.0)
    with pytest.raises(ConfirmationBlockedError):
        confirm_project(session, project, quote, confirmed_by="Estimator J.")
    assert project.state == "DISCOVERED"  # never touched


def test_confirming_an_override_required_quote_needs_a_reason(session):
    project, quote = _make_project_and_quote(session, gm_percent=28.0)
    with pytest.raises(ConfirmationRequiresOverrideReasonError):
        confirm_project(session, project, quote, confirmed_by="Estimator J.")
    assert project.state == "DISCOVERED"  # never touched


def test_confirming_an_override_required_quote_with_a_reason_succeeds(session):
    project, quote = _make_project_and_quote(session, gm_percent=28.0)
    confirmation = confirm_project(
        session, project, quote, confirmed_by="Management K.", override_reason="Strategic client, approved by management"
    )
    session.commit()

    assert project.state == "CONFIRMED"
    assert confirmation.override_reason == "Strategic client, approved by management"


def test_confirm_records_an_event(session):
    project, quote = _make_project_and_quote(session, gm_percent=35.0)
    confirmation = confirm_project(session, project, quote, confirmed_by="Estimator J.")
    session.commit()

    events = session.query(Event).filter_by(entity_type="confirmation", entity_id=confirmation.id).all()
    assert len(events) == 1
    assert events[0].payload["gate_status"] == "PASS"


def test_confirm_rejects_a_quote_belonging_to_a_different_project(session):
    project_a, _ = _make_project_and_quote(session, gm_percent=35.0)
    _, quote_b = _make_project_and_quote(session, gm_percent=35.0)

    with pytest.raises(ValueError):
        confirm_project(session, project_a, quote_b, confirmed_by="Estimator J.")
