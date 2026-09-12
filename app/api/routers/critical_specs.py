import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.core.models.critical_spec import CriticalSpec
from app.domain.state_machine import InvalidTransitionError
from app.domain.critical_specs import transition_critical_spec

router = APIRouter(prefix="/critical-specs", tags=["critical-specs"])


class TransitionCriticalSpecRequest(BaseModel):
    to_state: str
    confirmed_by: str | None = None


class CriticalSpecResponse(BaseModel):
    id: uuid.UUID
    spec_type: str
    state: str
    confirmed_by: str | None


@router.post("/{spec_id}/transition", response_model=CriticalSpecResponse)
def transition_critical_spec_route(
    spec_id: uuid.UUID,
    body: TransitionCriticalSpecRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("critical_spec", "DRAFT")),
) -> CriticalSpecResponse:
    """DRAFT-level for Discussion->Proposed; confirming (Proposed->Confirmed) is a business
    decision too, but C5 itself doesn't distinguish action levels per-state the way the GM30
    gate does, so this endpoint uses one consistent level throughout rather than inventing a
    finer split the Blueprint doesn't specify."""
    spec = db.get(CriticalSpec, spec_id)
    if spec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Critical spec not found")

    try:
        transition_critical_spec(db, spec, body.to_state, actor_user_id=user.id, confirmed_by=body.confirmed_by)
    except InvalidTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    db.commit()
    return CriticalSpecResponse(id=spec.id, spec_type=spec.spec_type, state=spec.state, confirmed_by=spec.confirmed_by)
