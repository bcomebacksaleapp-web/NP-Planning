from app.domain.feature_flags import is_enabled, set_enabled


def test_unknown_key_is_disabled_by_default(session):
    assert is_enabled(session, "never_created") is False


def test_set_enabled_creates_and_toggles(session):
    set_enabled(session, "canopy_configurator", True, description="Phase 1 vertical slice")
    session.commit()
    assert is_enabled(session, "canopy_configurator") is True

    set_enabled(session, "canopy_configurator", False)
    session.commit()
    assert is_enabled(session, "canopy_configurator") is False


def test_set_enabled_is_idempotent_on_the_key_not_a_duplicate_row(session):
    from sqlalchemy import select

    from app.core.models.feature_flag import FeatureFlag

    set_enabled(session, "same_key", True)
    set_enabled(session, "same_key", True)
    session.commit()

    rows = session.execute(select(FeatureFlag).where(FeatureFlag.key == "same_key")).scalars().all()
    assert len(rows) == 1
