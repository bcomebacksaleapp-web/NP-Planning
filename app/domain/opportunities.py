import uuid

from sqlalchemy.orm import Session

from app.core.models.opportunity import Opportunity
from app.core.models.project import Project
from app.domain.events import record_event
from app.domain.projects import create_project


def create_opportunity(
    session: Session, site_id: uuid.UUID, source: str, description: str | None = None
) -> Opportunity:
    opportunity = Opportunity(site_id=site_id, source=source, description=description)
    session.add(opportunity)
    session.flush()
    record_event(session, "opportunity", opportunity.id, "created", {"source": source})
    return opportunity


def convert_to_project(
    session: Session, opportunity: Opportunity, data: dict, actor_user_id: uuid.UUID | None = None
) -> Project:
    """Graduates an Opportunity into a real Project (Sprint 0.3's revision pattern handles the
    Project side). Once converted, the opportunity keeps existing -- it's not archived or
    deleted, since "this lead became this project" is itself a fact worth keeping (Law 5)."""
    project = create_project(session, opportunity.site_id, data, actor_user_id)
    opportunity.converted_to_project_id = project.id
    session.flush()
    record_event(
        session, "opportunity", opportunity.id, "converted_to_project", {"project_id": str(project.id)}, actor_user_id
    )
    return project
