import uuid

from sqlalchemy import select

from app.core.models.survey import SurveyObservation


def find_observations(session, site_id: uuid.UUID, knowledge_type: str | None = None) -> list[SurveyObservation]:
    """Returns raw observations, never a single aggregated "the answer".

    Part 16: a local observation must not automatically become a site-wide universal truth.
    Callers must show each observation's own applicability/confidence/source, not collapse
    several into one number -- this deliberately makes that collapsing harder to do by accident,
    by never doing it here.
    """
    query = select(SurveyObservation).where(SurveyObservation.site_id == site_id)
    if knowledge_type is not None:
        query = query.where(SurveyObservation.knowledge_type == knowledge_type)
    return list(session.execute(query.order_by(SurveyObservation.observed_date)).scalars())
