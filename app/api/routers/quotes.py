import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.core.models.project import Project
from app.core.models.quote import Quote
from app.domain.confirmations import (
    ConfirmationBlockedError,
    ConfirmationRequiresOverrideReasonError,
    confirm_project,
)

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
