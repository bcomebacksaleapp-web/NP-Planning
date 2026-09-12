import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.domain.canopy_configurator import configure_canopy_and_create_quote

router = APIRouter(prefix="/canopy", tags=["canopy"])


class ConfigureCanopyRequest(BaseModel):
    site_id: uuid.UUID
    width_m: float
    length_m: float
    roof_cover: str
    unit_cost_per_m2: float


class ConfigureCanopyResponse(BaseModel):
    project_id: uuid.UUID
    quote_id: uuid.UUID
    gate_status: str
    gm_percent: float
    selling_price: float


@router.post("/configure", response_model=ConfigureCanopyResponse)
def configure_canopy_route(
    body: ConfigureCanopyRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quote", "DRAFT")),
) -> ConfigureCanopyResponse:
    """Customer Mode's configurator (Part 12), wrapping app.domain.canopy_configurator --
    DRAFT-level, not COMMIT, per Law 14: this creates a real Quote, but it isn't a confirmed
    commitment until a staff member calls POST /quotes/confirm.

    Uses the manual unit_cost_per_m2 path only -- the Smart Fresh Price / supplier-quote path
    (app.domain.fresh_price) is real and tested at the domain layer but not yet exposed here;
    there's no real Supplier data to select from via this endpoint yet anyway.
    """
    project, quote = configure_canopy_and_create_quote(
        db, body.site_id, body.width_m, body.length_m, body.roof_cover,
        unit_cost_per_m2=body.unit_cost_per_m2, actor_user_id=user.id,
    )
    db.commit()

    from app.core.models.quote import QuoteRevision
    from app.domain.revisioning import latest_revision

    current = latest_revision(db, QuoteRevision, "quote_id", quote.id)
    return ConfigureCanopyResponse(
        project_id=project.id, quote_id=quote.id, gate_status=current.gate_status,
        gm_percent=current.gm_percent, selling_price=current.selling_price,
    )
