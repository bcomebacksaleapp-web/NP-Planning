from sqlalchemy import func, select
from sqlalchemy.orm import Session


def next_revision_number(session: Session, revision_model, parent_fk_attr: str, parent_id) -> int:
    """Generic next-revision-number lookup for the current-row + append-only-revision-table
    pattern (Law 4: restore creates a new revision, never rewrites history).

    Any future revisioned entity (Quote, Specification, WebsitePage, ...) should reuse this
    instead of reinventing per-entity numbering -- it's the one piece of the pattern that's
    genuinely identical across all of them.
    """
    current_max = session.execute(
        select(func.max(getattr(revision_model, "revision_number"))).where(
            getattr(revision_model, parent_fk_attr) == parent_id
        )
    ).scalar_one()
    return (current_max or 0) + 1


def latest_revision(session: Session, revision_model, parent_fk_attr: str, parent_id):
    """"Current" revision for the pattern above: the row with the highest revision_number.

    Deliberately derived by query rather than stored as a pointer column on the parent -- see
    app.core.models.project.Project's docstring for why (circular FK, breaks on SQLite).
    """
    return session.execute(
        select(revision_model)
        .where(getattr(revision_model, parent_fk_attr) == parent_id)
        .order_by(revision_model.revision_number.desc())
        .limit(1)
    ).scalar_one_or_none()
