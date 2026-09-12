from app.core.models.party import Customer, Site
from app.core.models.quote import QuoteRevision
from app.domain.pricing import selling_price_for_gm30
from app.domain.projects import create_project
from app.domain.quotes import create_quote, restore_quote_revision, update_quote
from app.domain.revisioning import latest_revision


def _price_for_gm(cost: float, gm_pct: float) -> float:
    return cost / (1 - gm_pct / 100)


def _make_project(session):
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    return create_project(session, site.id, {"name": "v1"})


def test_quote_at_gm30_passes_the_gate(session):
    project = _make_project(session)
    cost = 100_000
    quote = create_quote(
        session,
        project.id,
        true_cost=cost,
        selling_price=selling_price_for_gm30(cost),
        lines=[{"description": "Canopy install", "quantity": 1, "unit_price": selling_price_for_gm30(cost)}],
    )
    session.commit()

    current = latest_revision(session, QuoteRevision, "quote_id", quote.id)
    assert current.gate_status == "PASS"
    assert round(current.gm_percent, 2) == 30.0
    assert len(current.lines) == 1
    assert current.lines[0].line_total == selling_price_for_gm30(cost)


def test_quote_in_management_override_band(session):
    project = _make_project(session)
    cost = 100_000
    price = _price_for_gm(cost, 28.0)
    quote = create_quote(session, project.id, cost, price, [{"description": "x", "quantity": 1, "unit_price": price}])
    session.commit()

    current = latest_revision(session, QuoteRevision, "quote_id", quote.id)
    assert current.gate_status == "OVERRIDE_REQUIRED"
    assert "management" in current.gate_note.lower()


def test_quote_blocked_below_20_percent(session):
    project = _make_project(session)
    cost = 100_000
    price = _price_for_gm(cost, 10.0)
    quote = create_quote(session, project.id, cost, price, [{"description": "x", "quantity": 1, "unit_price": price}])
    session.commit()

    current = latest_revision(session, QuoteRevision, "quote_id", quote.id)
    assert current.gate_status == "BLOCKED"


def test_update_quote_creates_new_revision_and_old_lines_survive_unchanged(session):
    project = _make_project(session)
    cost = 100_000
    quote = create_quote(
        session, project.id, cost, selling_price_for_gm30(cost),
        [{"description": "v1 line", "quantity": 1, "unit_price": selling_price_for_gm30(cost)}],
    )
    update_quote(
        session, quote, cost, _price_for_gm(cost, 25.0),
        [{"description": "v2 line", "quantity": 2, "unit_price": 60_000}],
    )
    session.commit()

    revisions = (
        session.query(QuoteRevision).filter_by(quote_id=quote.id).order_by(QuoteRevision.revision_number).all()
    )
    assert [r.revision_number for r in revisions] == [1, 2]
    assert revisions[0].lines[0].description == "v1 line"  # untouched
    assert revisions[0].gate_status == "PASS"
    assert revisions[1].lines[0].description == "v2 line"
    assert revisions[1].gate_status == "OVERRIDE_REQUIRED"


def test_restore_quote_revision_copies_price_and_lines_and_leaves_history_untouched(session):
    project = _make_project(session)
    cost = 100_000
    quote = create_quote(
        session, project.id, cost, selling_price_for_gm30(cost),
        [{"description": "v1 line", "quantity": 1, "unit_price": selling_price_for_gm30(cost)}],
    )
    update_quote(session, quote, cost, _price_for_gm(cost, 15.0), [{"description": "v2 line", "quantity": 1, "unit_price": 1}])
    session.commit()

    restored = restore_quote_revision(session, quote, target_revision_number=1)
    session.commit()

    assert restored.revision_number == 3
    assert restored.true_cost == cost
    assert restored.selling_price == selling_price_for_gm30(cost)
    assert restored.gate_status == "PASS"
    assert restored.restored_from_revision_number == 1
    assert restored.lines[0].description == "v1 line"

    revisions = (
        session.query(QuoteRevision).filter_by(quote_id=quote.id).order_by(QuoteRevision.revision_number).all()
    )
    assert [r.revision_number for r in revisions] == [1, 2, 3]
    assert revisions[1].gate_status == "BLOCKED"  # untouched
