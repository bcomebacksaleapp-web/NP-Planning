import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.domain.site_knowledge import find_observations
from app.domain.unknown_radar import survey_checklist

router = APIRouter(prefix="/sites", tags=["site-knowledge"])


class ObservationResponse(BaseModel):
    id: uuid.UUID
    knowledge_type: str
    location_description: str
    observed_value: str | None
    confidence: str | None
    applicability: str
    verified_by: str | None


@router.get("/{site_id}/knowledge", response_model=list[ObservationResponse])
def site_knowledge_route(
    site_id: uuid.UUID,
    knowledge_type: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_permission("site_knowledge", "READ")),
) -> list[ObservationResponse]:
    """Part 16: never a single collapsed 'answer' -- returns every observation on record, each
    with its own applicability/confidence, exactly as app.domain.site_knowledge.find_observations
    already guarantees at the domain layer."""
    observations = find_observations(db, site_id, knowledge_type)
    return [
        ObservationResponse(
            id=o.id, knowledge_type=o.knowledge_type, location_description=o.location_description,
            observed_value=o.observed_value, confidence=o.confidence, applicability=o.applicability,
            verified_by=o.verified_by,
        )
        for o in observations
    ]


@router.get("/{site_id}/survey-checklist")
def survey_checklist_route(
    site_id: uuid.UUID,
    knowledge_types: str,
    db: Session = Depends(get_db),
    user=Depends(require_permission("site_knowledge", "READ")),
) -> dict:
    """Part 13.4: which of the given (caller-supplied) knowledge types still need survey
    attention. `knowledge_types` is a comma-separated query param -- e.g.
    ?knowledge_types=pile_depth,soil_bearing."""
    types = [t.strip() for t in knowledge_types.split(",") if t.strip()]
    return survey_checklist(db, site_id, types)
