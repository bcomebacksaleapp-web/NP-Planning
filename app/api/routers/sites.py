import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.core.models.party import SITE_TYPES
from app.domain.site import create_site, get_or_create_customer

router = APIRouter(prefix="/sites", tags=["sites"])


class CreateSiteRequest(BaseModel):
    customer_name: str
    site_type: str
    name: str
    address: str | None = None


class SiteResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    site_type: str
    name: str
    address: str | None


@router.post("", response_model=SiteResponse)
def create_site_route(
    body: CreateSiteRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("site", "DRAFT")),
) -> SiteResponse:
    """customer_name is get-or-create (app.domain.site.get_or_create_customer) so callers don't
    need a separate step to look up or create the Customer first. site_type is validated against
    the fixed HOME/OFFICE/FACTORY vocabulary (Part 15) the same way the DB CHECK constraint does,
    just with a clearer error message at the API boundary.
    """
    if body.site_type not in SITE_TYPES:
        raise HTTPException(422, f"site_type must be one of {SITE_TYPES}")

    customer = get_or_create_customer(db, body.customer_name, actor_user_id=user.id)
    site = create_site(db, customer.id, body.site_type, body.name, body.address, actor_user_id=user.id)
    db.commit()
    return SiteResponse(
        id=site.id, customer_id=site.customer_id, site_type=site.site_type,
        name=site.name, address=site.address,
    )
