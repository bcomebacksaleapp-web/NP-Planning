from app.core.models.critical_spec import CriticalSpec
from app.core.models.party import Customer, Site
from app.domain.next_best_action import recommend_for_critical_spec, recommend_for_quote
from app.domain.projects import create_project
from app.domain.quotes import create_quote


def _make_project(session):
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    return create_project(session, site.id, {})


def _price_for_gm(cost: float, gm_pct: float) -> float:
    return cost / (1 - gm_pct / 100)


def test_blocked_quote_recommends_revising_pricing(session):
    project = _make_project(session)
    cost = 100_000
    quote = create_quote(session, project.id, cost, _price_for_gm(cost, 10.0), [{"description": "x", "quantity": 1, "unit_price": 1}])
    session.commit()

    actions = recommend_for_quote(session, quote)
    assert len(actions) == 1
    assert "blocked" in actions[0].issue.lower()
    assert actions[0].allowed_next_action == "DRAFT"


def test_override_required_quote_recommends_obtaining_sign_off(session):
    project = _make_project(session)
    cost = 100_000
    quote = create_quote(session, project.id, cost, _price_for_gm(cost, 28.0), [{"description": "x", "quantity": 1, "unit_price": 1}])
    session.commit()

    actions = recommend_for_quote(session, quote)
    assert len(actions) == 1
    assert "override" in actions[0].issue.lower()
    assert actions[0].allowed_next_action == "SUGGEST"


def test_passing_quote_has_no_recommendations(session):
    project = _make_project(session)
    cost = 100_000
    quote = create_quote(session, project.id, cost, _price_for_gm(cost, 35.0), [{"description": "x", "quantity": 1, "unit_price": 1}])
    session.commit()

    assert recommend_for_quote(session, quote) == []


def test_critical_spec_in_discussion_recommends_advancing(session):
    project = _make_project(session)
    spec = CriticalSpec(project_id=project.id, spec_type="roof_material_model", description="TBD")
    session.add(spec)
    session.commit()

    actions = recommend_for_critical_spec(spec)
    assert len(actions) == 1
    assert "discussion" in actions[0].issue.lower()


def test_critical_spec_proposed_recommends_confirming(session):
    project = _make_project(session)
    spec = CriticalSpec(project_id=project.id, spec_type="roof_material_model", description="TN Polycarbonate", state="PROPOSED")
    session.add(spec)
    session.commit()

    actions = recommend_for_critical_spec(spec)
    assert len(actions) == 1
    assert "confirm" in actions[0].recommended_action.lower()


def test_critical_spec_confirmed_has_no_recommendations(session):
    project = _make_project(session)
    spec = CriticalSpec(
        project_id=project.id, spec_type="roof_material_model", description="TN Polycarbonate",
        state="CONFIRMED", confirmed_by="Estimator J.",
    )
    session.add(spec)
    session.commit()

    assert recommend_for_critical_spec(spec) == []


def test_no_action_recommends_anything_stronger_than_suggest_or_draft(session):
    """Law 14: nothing this module recommends may require COMMIT-level autonomy."""
    project = _make_project(session)
    cost = 100_000
    blocked_quote = create_quote(session, project.id, cost, _price_for_gm(cost, 10.0), [{"description": "x", "quantity": 1, "unit_price": 1}])
    override_quote = create_quote(session, project.id, cost, _price_for_gm(cost, 28.0), [{"description": "x", "quantity": 1, "unit_price": 1}])
    session.commit()

    all_actions = recommend_for_quote(session, blocked_quote) + recommend_for_quote(session, override_quote)
    assert all(a.allowed_next_action in ("READ", "SUGGEST", "DRAFT") for a in all_actions)
