import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models.project import Project, ProjectRevision
from app.domain.events import record_event
from app.domain.revisioning import next_revision_number


def create_project(
    session: Session, site_id: uuid.UUID, data: dict, actor_user_id: uuid.UUID | None = None
) -> Project:
    """Creates a Project and its first revision (revision_number=1) as one unit."""
    project = Project(site_id=site_id)
    session.add(project)
    session.flush()  # project.id must exist before a ProjectRevision can reference it

    session.add(ProjectRevision(project_id=project.id, revision_number=1, data=data))
    session.flush()
    record_event(session, "project", project.id, "created", {"revision_number": 1}, actor_user_id)
    return project


def update_project(
    session: Session, project: Project, data: dict, actor_user_id: uuid.UUID | None = None
) -> ProjectRevision:
    """Creates a new revision holding `data`. Never mutates an existing ProjectRevision row."""
    revision_number = next_revision_number(session, ProjectRevision, "project_id", project.id)
    revision = ProjectRevision(project_id=project.id, revision_number=revision_number, data=data)
    session.add(revision)
    session.flush()
    record_event(
        session, "project", project.id, "revision_created", {"revision_number": revision_number}, actor_user_id
    )
    return revision


def restore_project_revision(
    session: Session,
    project: Project,
    target_revision_number: int,
    actor_user_id: uuid.UUID | None = None,
) -> ProjectRevision:
    """Law 4: restoring Rev N creates a NEW revision copying Rev N's data. It never touches the
    old row at all.

    Example from the Blueprint: Rev 12 -> Rev 13 -> Rev 14, restore Rev 12 -> creates Rev 15
    (based on Rev 12's data). Rev 12, 13, 14 remain exactly as they were.
    """
    target = session.execute(
        select(ProjectRevision).where(
            ProjectRevision.project_id == project.id,
            ProjectRevision.revision_number == target_revision_number,
        )
    ).scalar_one()

    new_revision_number = next_revision_number(session, ProjectRevision, "project_id", project.id)
    revision = ProjectRevision(
        project_id=project.id,
        revision_number=new_revision_number,
        data=dict(target.data),
        restored_from_revision_number=target.revision_number,
    )
    session.add(revision)
    session.flush()
    record_event(
        session,
        "project",
        project.id,
        "revision_restored",
        {"revision_number": new_revision_number, "restored_from_revision_number": target.revision_number},
        actor_user_id,
    )
    return revision
