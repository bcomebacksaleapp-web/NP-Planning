from app.core.models.supplier import SupplierQuote
from app.domain.fresh_price import PriceQuote


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
