import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.core.models.inquiry import WebsiteInquiry
from app.core.models.party import SITE_TYPES
from app.domain.inquiries import InquiryAlreadyConvertedError, convert_inquiry_to_opportunity, create_inquiry, list_inquiries

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


class ConvertInquiryRequest(BaseModel):
    customer_name: str
    site_type: str
    site_name: str
    site_address: str | None = None


class ConvertInquiryResponse(BaseModel):
    inquiry: InquiryResponse
    customer_id: uuid.UUID
    site_id: uuid.UUID
    opportunity_id: uuid.UUID


@router.post("/{inquiry_id}/convert", response_model=ConvertInquiryResponse)
def convert_inquiry_route(
    inquiry_id: uuid.UUID, body: ConvertInquiryRequest, db: Session = Depends(get_db),
    user=Depends(require_permission("website_inquiry", "DRAFT")),
) -> ConvertInquiryResponse:
    """The action behind the "still a manual step" note that used to sit on the Inquiries tab --
    turns a raw lead into a real Customer + Site + Opportunity, same domain calls POST /sites
    and POST /opportunities use individually, just composed into one staff action."""
    if body.site_type not in SITE_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"site_type must be one of {SITE_TYPES}")

    inquiry = db.get(WebsiteInquiry, inquiry_id)
    if inquiry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Inquiry not found")

    try:
        customer, site, opportunity = convert_inquiry_to_opportunity(
            db, inquiry, body.customer_name, body.site_type, body.site_name, body.site_address,
            actor_user_id=user.id,
        )
    except InquiryAlreadyConvertedError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    db.commit()
    return ConvertInquiryResponse(
        inquiry=_response(inquiry), customer_id=customer.id, site_id=site.id, opportunity_id=opportunity.id,
    )
