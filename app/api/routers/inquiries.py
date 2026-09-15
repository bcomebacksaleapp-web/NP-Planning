import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.domain.inquiries import create_inquiry, list_inquiries

router = APIRouter(prefix="/inquiries", tags=["inquiries"])


class CreateInquiryRequest(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    service_interest: str | None = None
    message: str | None = None
    source_page: str | None = None


class InquiryResponse(BaseModel):
    id: uuid.UUID
    name: str
    phone: str | None
    email: str | None
    service_interest: str | None
    message: str | None
    source_page: str | None
    converted_to_opportunity_id: uuid.UUID | None
    created_at: datetime


def _response(inquiry) -> InquiryResponse:
    return InquiryResponse(
        id=inquiry.id, name=inquiry.name, phone=inquiry.phone, email=inquiry.email,
        service_interest=inquiry.service_interest, message=inquiry.message,
        source_page=inquiry.source_page, converted_to_opportunity_id=inquiry.converted_to_opportunity_id,
        created_at=inquiry.created_at,
    )


@router.post("", response_model=InquiryResponse)
def create_inquiry_route(body: CreateInquiryRequest, db: Session = Depends(get_db)) -> InquiryResponse:
    """Deliberately no auth -- this is what the public contact form on /site submits to. Every
    other write in this system requires a logged-in staff member; this is the one exception,
    same reasoning as GET /website/pages/{branch}/{slug} being the one unauthenticated read."""
    inquiry = create_inquiry(
        db, body.name, body.phone, body.email, body.service_interest, body.message, body.source_page,
    )
    db.commit()
    return _response(inquiry)


@router.get("", response_model=list[InquiryResponse])
def list_inquiries_route(
    db: Session = Depends(get_db), user=Depends(require_permission("website_inquiry", "READ")),
) -> list[InquiryResponse]:
    return [_response(i) for i in list_inquiries(db)]
