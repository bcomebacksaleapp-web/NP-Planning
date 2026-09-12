from app.core.models.party import Customer, Site
from app.core.models.survey import SurveyObservation
from app.domain.unknown_radar import KNOWN, PARTIAL, UNKNOWN, classify_knowledge, survey_checklist


def _make_site(session) -> Site:
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    return site


def test_no_observations_is_unknown(session):
    site = _make_site(session)
    assert classify_knowledge(session, site.id, "pile_depth") == UNKNOWN


def test_unverified_observation_is_partial(session):
    site = _make_site(session)
    session.add(
        SurveyObservation(
            site_id=site.id, knowledge_type="pile_depth", location_description="Near Driver Room",
            description="Observed during excavation", source="Job X", applicability="local",
        )
    )
    session.commit()
    assert classify_knowledge(session, site.id, "pile_depth") == PARTIAL


def test_verified_observation_is_known(session):
    site = _make_site(session)
    session.add(
        SurveyObservation(
            site_id=site.id, knowledge_type="pile_depth", location_description="Near Driver Room",
            description="Observed during excavation", source="Job X", applicability="local",
            verified_by="Site Engineer P.",
        )
    )
    session.commit()
    assert classify_knowledge(session, site.id, "pile_depth") == KNOWN


def test_survey_checklist_classifies_each_knowledge_type_independently(session):
    site = _make_site(session)
    session.add(
        SurveyObservation(
            site_id=site.id, knowledge_type="pile_depth", location_description="A",
            description="d", source="s", applicability="a", verified_by="Engineer",
        )
    )
    session.commit()

    checklist = survey_checklist(session, site.id, ["pile_depth", "soil_bearing", "access_constraint"])
    assert checklist == {
        "pile_depth": KNOWN,
        "soil_bearing": UNKNOWN,
        "access_constraint": UNKNOWN,
    }
