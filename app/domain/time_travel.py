from datetime import datetime

from sqlalchemy import select


def revision_as_of(
    session,
    revision_model,
    parent_fk_attr: str,
    parent_id,
    as_of: datetime,
    number_attr: str = "revision_number",
):
    """The revision that was current at a given point in time: the latest revision created at or
    before `as_of`.

    This is the data-model meaning of Blueprint Part 8's "View Factory A as of 15 Mar 2026" --
    it must never surface a revision created after that date, since that information wasn't
    known yet as of the date being viewed. Returns None if no revision existed yet at that time.

    `number_attr` matches app.domain.revisioning's helpers -- defaults to "revision_number" but
    is a parameter for entities that name their column something else (e.g. RecipeVersion.version_number).
    """
    return session.execute(
        select(revision_model)
        .where(
            getattr(revision_model, parent_fk_attr) == parent_id,
            revision_model.created_at <= as_of,
        )
        .order_by(getattr(revision_model, number_attr).desc())
        .limit(1)
    ).scalar_one_or_none()
