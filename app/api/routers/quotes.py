import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.core.models.project import Project
from app.core.models.quote import Quote, QuoteRevision
from app.domain.confirmations import (
    ConfirmationBlockedError,
    ConfirmationRequiresOverrideReasonError,
    confirm_project,
)
from app.domain.next_best_action import recommend_for_quote
from app.domain.revisioning import latest_revision
from app.domain.what_if import WhatIfResult, simulate_cost_change, simulate_discount

router = APIRouter(prefix="/quotes", tags=["quotes"])


class ConfirmQuoteRequest(BaseModel):
    project_id: uuid.UUID
    quote_id: uuid.UUID
    confirmed_by: str
    override_reason: str | None = None


class ConfirmQuoteResponse(BaseModel):
    confirmation_id: uuid.UUID
    project_state: str
    confirmed_quote_revision_number: int


@router.post("/confirm", response_model=ConfirmQuoteResponse)
def confirm_quote_route(
    body: ConfirmQuoteRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quote", "COMMIT")),
) -> ConfirmQuoteResponse:
    """Confirming is COMMIT-level (Law 14) -- consequential, requires explicit human
    authorization, distinct from the DRAFT-level configure step in app/api/routers/canopy.py.
    """
    project = db.get(Project, body.project_id)
    quote = db.get(Quote, body.quote_id)
    if project is None or quote is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project or quote not found")

    try:
        confirmation = confirm_project(
            db, project, quote, body.confirmed_by, body.override_reason, actor_user_id=user.id
        )
    except ConfirmationBlockedError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except ConfirmationRequiresOverrideReasonError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    db.commit()
    return ConfirmQuoteResponse(
        confirmation_id=confirmation.id, project_state=project.state,
        confirmed_quote_revision_number=confirmation.confirmed_quote_revision_number,
    )


class WhatIfRequest(BaseModel):
    cost_change_percent: float | None = None
    discount_percent: float | None = None


class WhatIfResponse(BaseModel):
    scenario: str
    hypothetical_true_cost: float
    hypothetical_selling_price: float
    hypothetical_gm_percent: float
    gate_status: str
    gate_note: str


@router.post("/{quote_id}/what-if", response_model=WhatIfResponse)
def what_if_route(
    quote_id: uuid.UUID,
    body: WhatIfRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quote", "READ")),
) -> WhatIfResponse:
    """Part 13.8. Read-only -- never writes a new revision, just re-evaluates the existing
    GM30/gate logic against a hypothetical. Exactly one of cost_change_percent/discount_percent
    must be given, mirroring canopy_configurator's "exactly one cost source" pattern."""
    if (body.cost_change_percent is None) == (body.discount_percent is None):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Supply exactly one of cost_change_percent or discount_percent")

    current = latest_revision(db, QuoteRevision, "quote_id", quote_id)
    if current is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quote not found")

    result: WhatIfResult
    if body.cost_change_percent is not None:
        result = simulate_cost_change(current.true_cost, current.selling_price, body.cost_change_percent)
    else:
        result = simulate_discount(current.true_cost, current.selling_price, body.discount_percent)

    return WhatIfResponse(**result.__dict__)


class NextBestActionResponse(BaseModel):
    issue: str
    why: str
    risk: str
    recommended_action: str
    allowed_next_action: str


@router.get("/{quote_id}/recommendations", response_model=list[NextBestActionResponse])
def quote_recommendations_route(
    quote_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quote", "READ")),
) -> list[NextBestActionResponse]:
    quote = db.get(Quote, quote_id)
    if quote is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quote not found")

    actions = recommend_for_quote(db, quote)
    return [NextBestActionResponse(**a.__dict__) for a in actions]
