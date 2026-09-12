from app.core.models.event import Event
from app.core.models.party import Customer, Site
from app.domain.site_quality import active_flags_for_site, flag_site, is_healthy, resolve_flag


def _make_site(session) -> Site:
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    return site


def test_site_with_no_flags_is_healthy(session):
    site = _make_site(session)
    assert is_healthy(session, site.id) is True


def test_flagging_a_site_makes_it_unhealthy(session):
    site = _make_site(session)
    flag_site(session, site.id, "BAD_PAYMENT", "Consistently 60+ days late", flagged_by="PM K.")
    session.commit()

    assert is_healthy(session, site.id) is False
    assert len(active_flags_for_site(session, site.id)) == 1


def test_resolving_the_only_flag_makes_it_healthy_again(session):
    site = _make_site(session)
    flag = flag_site(session, site.id, "HIGH_DISPUTE", "Repeated scope disputes", flagged_by="PM K.")
    session.commit()

    resolve_flag(session, flag)
    session.commit()

    assert is_healthy(session, site.id) is True
    assert active_flags_for_site(session, site.id) == []


def test_resolved_flags_do_not_count_toward_active(session):
    site = _make_site(session)
    old_flag = flag_site(session, site.id, "MARGIN_LEAKAGE", "Old issue, since resolved", flagged_by="PM K.")
    resolve_flag(session, old_flag)
    new_flag = flag_site(session, site.id, "UNSAFE_PRACTICES", "New issue", flagged_by="Site Engineer P.")
    session.commit()

    active = active_flags_for_site(session, site.id)
    assert len(active) == 1
    assert active[0].id == new_flag.id


def test_flagging_and_resolving_record_events(session):
    site = _make_site(session)
    flag = flag_site(session, site.id, "POOR_CAPACITY_FIT", "Overloads the crew every time", flagged_by="PM K.")
    resolve_flag(session, flag)
    session.commit()

    events = session.query(Event).filter_by(entity_type="site", entity_id=site.id).all()
    assert [e.event_type for e in events] == ["quality_flagged", "quality_flag_resolved"]
