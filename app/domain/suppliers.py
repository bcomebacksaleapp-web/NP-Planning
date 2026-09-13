import uuid
from datetime import date

from sqlalchemy import select

from app.core.models.supplier import Supplier, SupplierQuote
from app.domain.events import record_event
from app.domain.fresh_price import PriceQuote


def get_or_create_supplier(session, name: str, actor_user_id: uuid.UUID | None = None) -> Supplier:
    """Idempotent on `name`, same shape as app.domain.recipes.get_or_create_product -- callers
    that just need "the Supplier row for X" shouldn't have to separately track whether it's
    been created yet."""
    supplier = session.execute(select(Supplier).where(Supplier.name == name)).scalar_one_or_none()
    if supplier is not None:
        return supplier
    supplier = Supplier(name=name)
    session.add(supplier)
    session.flush()
    record_event(session, "supplier", supplier.id, "created", {"name": name}, actor_user_id)
    return supplier


def create_supplier_quote(
    session,
    supplier_id: uuid.UUID,
    material_description: str,
    quoted_price: float,
    quote_date: date,
    validity_days: int,
    lock_days: int,
    lead_time_days: int,
    moq: float | None = None,
    actor_user_id: uuid.UUID | None = None,
) -> SupplierQuote:
    """Like create_critical_spec, this didn't exist until trying to exercise the API end-to-end
    surfaced that there was no way to create a SupplierQuote through it at all -- only
    record_actual_procurement against one that already existed. Every other create_X function
    records a "created" event; this now does too."""
    quote = SupplierQuote(
        supplier_id=supplier_id, material_description=material_description, quoted_price=quoted_price,
        quote_date=quote_date, validity_days=validity_days, lock_days=lock_days,
        lead_time_days=lead_time_days, moq=moq,
    )
    session.add(quote)
    session.flush()
    record_event(
        session, "supplier_quote", quote.id, "created",
        {"material_description": material_description, "quoted_price": quoted_price}, actor_user_id,
    )
    return quote


def to_price_quote(supplier_quote: SupplierQuote) -> PriceQuote:
    """Adapter from a persisted SupplierQuote row to the pure PriceQuote type
    app.domain.fresh_price's algorithms operate on."""
    return PriceQuote(
        price=supplier_quote.quoted_price,
        lock_days=supplier_quote.lock_days,
        source=str(supplier_quote.supplier_id),
    )


def record_actual_procurement(
    session, supplier_quote: SupplierQuote, actual_price: float, actual_lead_time_days: int
) -> None:
    """Fills in what actually happened after a quote was acted on -- quoted vs. actual is
    exactly the distinction Part 13.7 asks for."""
    supplier_quote.actual_procurement_price = actual_price
    supplier_quote.actual_lead_time_days = actual_lead_time_days
    session.flush()
