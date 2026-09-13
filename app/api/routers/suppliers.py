import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.core.models.supplier import SupplierQuote
from app.domain.suppliers import create_supplier_quote, get_or_create_supplier, record_actual_procurement

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


class CreateSupplierRequest(BaseModel):
    name: str


class SupplierResponse(BaseModel):
    id: uuid.UUID
    name: str


@router.post("", response_model=SupplierResponse)
def create_supplier_route(
    body: CreateSupplierRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("supplier_quote", "DRAFT")),
) -> SupplierResponse:
    """Idempotent on name (app.domain.suppliers.get_or_create_supplier) -- calling this twice
    with the same name returns the same Supplier, not a duplicate."""
    supplier = get_or_create_supplier(db, body.name, actor_user_id=user.id)
    db.commit()
    return SupplierResponse(id=supplier.id, name=supplier.name)


class CreateSupplierQuoteRequest(BaseModel):
    supplier_id: uuid.UUID
    material_description: str
    quoted_price: float
    quote_date: date
    validity_days: int
    lock_days: int
    lead_time_days: int
    moq: float | None = None


class RecordActualProcurementRequest(BaseModel):
    actual_price: float
    actual_lead_time_days: int


class SupplierQuoteResponse(BaseModel):
    id: uuid.UUID
    quoted_price: float
    actual_procurement_price: float | None
    actual_lead_time_days: int | None


@router.post("/quotes", response_model=SupplierQuoteResponse)
def create_supplier_quote_route(
    body: CreateSupplierQuoteRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("supplier_quote", "DRAFT")),
) -> SupplierQuoteResponse:
    quote = create_supplier_quote(
        db, body.supplier_id, body.material_description, body.quoted_price, body.quote_date,
        body.validity_days, body.lock_days, body.lead_time_days, body.moq, actor_user_id=user.id,
    )
    db.commit()
    return SupplierQuoteResponse(
        id=quote.id, quoted_price=quote.quoted_price,
        actual_procurement_price=quote.actual_procurement_price, actual_lead_time_days=quote.actual_lead_time_days,
    )


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
