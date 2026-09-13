from datetime import date

from app.core.models.event import Event
from app.core.models.supplier import Supplier, SupplierQuote
from app.domain.fresh_price import market_reference_price, select_procurement_quote
from app.domain.suppliers import create_supplier_quote, get_or_create_supplier, record_actual_procurement, to_price_quote


def _make_quote(session, supplier_name, price, lock_days):
    supplier = Supplier(name=supplier_name)
    session.add(supplier)
    session.flush()
    quote = SupplierQuote(
        supplier_id=supplier.id,
        material_description="Metal Sheet Roofing, 0.35mm",
        quoted_price=price,
        quote_date=date(2026, 1, 1),
        validity_days=14,
        lock_days=lock_days,
        lead_time_days=21,
    )
    session.add(quote)
    session.flush()
    return quote


def test_to_price_quote_carries_price_and_lock_days(session):
    quote = _make_quote(session, "Supplier A", 98.0, 30)
    price_quote = to_price_quote(quote)
    assert price_quote.price == 98.0
    assert price_quote.lock_days == 30
    assert price_quote.source == str(quote.supplier_id)


def test_real_supplier_quotes_feed_directly_into_fresh_price_algorithms(session):
    """Confirms the adapter actually plugs into fresh_price's functions, not just that the
    fields copy over correctly."""
    quotes = [
        _make_quote(session, "A", 98.0, 30),
        _make_quote(session, "B", 101.0, 60),
        _make_quote(session, "C", 105.0, 90),
    ]
    price_quotes = [to_price_quote(q) for q in quotes]

    assert market_reference_price(price_quotes) == 101.0
    selected = select_procurement_quote(price_quotes, required_lock_days=90)
    assert selected.price == 105.0


def test_record_actual_procurement_fills_actuals_without_touching_the_quoted_fields(session):
    quote = _make_quote(session, "Supplier A", 98.0, 30)

    record_actual_procurement(session, quote, actual_price=99.5, actual_lead_time_days=25)
    session.commit()

    assert quote.actual_procurement_price == 99.5
    assert quote.actual_lead_time_days == 25
    assert quote.quoted_price == 98.0  # untouched
    assert quote.lead_time_days == 21  # untouched


def test_get_or_create_supplier_is_idempotent_on_name(session):
    first = get_or_create_supplier(session, "Supplier A")
    second = get_or_create_supplier(session, "Supplier A")
    session.commit()
    assert first.id == second.id


def test_get_or_create_supplier_records_an_event_only_on_first_creation(session):
    get_or_create_supplier(session, "Supplier A")
    get_or_create_supplier(session, "Supplier A")
    session.commit()

    supplier = get_or_create_supplier(session, "Supplier A")
    events = session.query(Event).filter_by(entity_type="supplier", entity_id=supplier.id).all()
    assert len(events) == 1


def test_create_supplier_quote_records_an_event(session):
    supplier = get_or_create_supplier(session, "Supplier A")
    quote = create_supplier_quote(
        session, supplier.id, "Metal Sheet Roofing, 0.35mm", 98.0, date(2026, 1, 1),
        validity_days=14, lock_days=30, lead_time_days=21,
    )
    session.commit()

    events = session.query(Event).filter_by(entity_type="supplier_quote", entity_id=quote.id).all()
    assert len(events) == 1
    assert events[0].payload["quoted_price"] == 98.0
    assert quote.supplier_id == supplier.id
    assert quote.moq is None
