import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.core.models.supplier import SupplierQuote
from app.domain.suppliers import record_actual_procurement

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


class RecordActualProcurementRequest(BaseModel):
    actual_price: float
    actual_lead_time_days: int


class SupplierQuoteResponse(BaseModel):
    id: uuid.UUID
    quoted_price: float
    actual_procurement_price: float | None
    actual_lead_time_days: int | None


@router.post("/quotes/{quote_id}/actual-procurement", response_model=SupplierQuoteResponse)
def record_actual_procurement_route(
    quote_id: uuid.UUID,
    body: RecordActualProcurementRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("supplier_quote", "DRAFT")),
) -> SupplierQuoteResponse:
    """Quoted vs. actual (Part 13.7) -- the quoted fields are never touched, only the actual_*
    ones are filled in, exactly as app.domain.suppliers.record_actual_procurement already
    guarantees at the domain layer."""
    quote = db.get(SupplierQuote, quote_id)
    if quote is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier quote not found")

    record_actual_procurement(db, quote, body.actual_price, body.actual_lead_time_days)
    db.commit()
    return SupplierQuoteResponse(
        id=quote.id, quoted_price=quote.quoted_price,
        actual_procurement_price=quote.actual_procurement_price, actual_lead_time_days=quote.actual_lead_time_days,
    )
