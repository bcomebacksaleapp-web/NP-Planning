import uuid

from sqlalchemy import select

from app.core.db import utcnow
from app.core.models.site_quality_flag import SiteQualityFlag
from app.domain.events import record_event


def flag_site(
    session,
    site_id: uuid.UUID,
    flag_type: str,
    description: str,
    flagged_by: str,
    actor_user_id: uuid.UUID | None = None,
) -> SiteQualityFlag:
    flag = SiteQualityFlag(site_id=site_id, flag_type=flag_type, description=description, flagged_by=flagged_by)
    session.add(flag)
    session.flush()
    record_event(session, "site", site_id, "quality_flagged", {"flag_type": flag_type}, actor_user_id)
    return flag


def resolve_flag(session, flag: SiteQualityFlag, actor_user_id: uuid.UUID | None = None) -> None:
    flag.resolved_at = utcnow()
    session.flush()
    record_event(session, "site", flag.site_id, "quality_flag_resolved", {"flag_type": flag.flag_type}, actor_user_id)


def active_flags_for_site(session, site_id: uuid.UUID) -> list[SiteQualityFlag]:
    return list(
        session.execute(
            select(SiteQualityFlag).where(
                SiteQualityFlag.site_id == site_id, SiteQualityFlag.resolved_at.is_(None)
            )
        ).scalars()
    )


def is_healthy(session, site_id: uuid.UUID) -> bool:
    """A site with no unresolved quality flags is healthy -- deliberately binary, not a scored
    composite (the Blueprint gives no formula for a graded health score here)."""
    return len(active_flags_for_site(session, site_id)) == 0
