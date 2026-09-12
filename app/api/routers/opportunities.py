import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.core.models.opportunity import Opportunity
from app.domain.opportunities import convert_to_project, create_opportunity

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


class CreateOpportunityRequest(BaseModel):
    site_id: uuid.UUID
    source: str
    description: str | None = None


class OpportunityResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    source: str
    converted_to_project_id: uuid.UUID | None


class ConvertOpportunityRequest(BaseModel):
    project_data: dict = {}


class ConvertOpportunityResponse(BaseModel):
    project_id: uuid.UUID
    project_state: str


@router.post("", response_model=OpportunityResponse)
def create_opportunity_route(
    body: CreateOpportunityRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("opportunity", "DRAFT")),
) -> OpportunityResponse:
    opportunity = create_opportunity(db, body.site_id, body.source, body.description)
    db.commit()
    return OpportunityResponse(
        id=opportunity.id, site_id=opportunity.site_id, source=opportunity.source,
        converted_to_project_id=opportunity.converted_to_project_id,
    )


@router.post("/{opportunity_id}/convert", response_model=ConvertOpportunityResponse)
def convert_opportunity_route(
    opportunity_id: uuid.UUID,
    body: ConvertOpportunityRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project", "DRAFT")),
) -> ConvertOpportunityResponse:
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Opportunity not found")

    project = convert_to_project(db, opportunity, body.project_data, actor_user_id=user.id)
    db.commit()
    return ConvertOpportunityResponse(project_id=project.id, project_state=project.state)
