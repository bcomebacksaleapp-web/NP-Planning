from sqlalchemy import select

from app.core.models.feature_flag import FeatureFlag


def is_enabled(session, key: str) -> bool:
    """A key with no row is disabled -- fails closed on a typo'd or not-yet-created key."""
    flag = session.execute(select(FeatureFlag).where(FeatureFlag.key == key)).scalar_one_or_none()
    return flag.enabled if flag is not None else False


def set_enabled(session, key: str, enabled: bool, description: str | None = None) -> FeatureFlag:
    flag = session.execute(select(FeatureFlag).where(FeatureFlag.key == key)).scalar_one_or_none()
    if flag is None:
        flag = FeatureFlag(key=key, enabled=enabled, description=description)
        session.add(flag)
    else:
        flag.enabled = enabled
        if description is not None:
            flag.description = description
    session.flush()
    return flag
