from datetime import date

from app.core.models.party import Customer, Site
from app.core.models.survey import SurveyObservation
from app.domain.site_knowledge import find_observations


def _make_site(session) -> Site:
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    return site


def test_observation_stores_the_part16_field_set(session):
    """Encodes Part 16's own worked example directly: never "Factory A piles = 9m", instead a
    bounded, sourced, dated observation with explicit applicability."""
    site = _make_site(session)
    obs = SurveyObservation(
        site_id=site.id,
        knowledge_type="pile_depth",
        location_description="Near Driver Room",
        description="Previous pile work observed during excavation",
        original_assumption="15m assumed at initial estimate",
        observed_value="<=9m",
        source="Job X site records",
        observed_date=date(2025, 3, 10),
        confidence="medium",
        applicability="Limited to this local area (near Driver Room) unless verified elsewhere",
        verified_by="Site Engineer P.",
    )
    session.add(obs)
    session.commit()

    fetched = session.get(SurveyObservation, obs.id)
    assert fetched.observed_value == "<=9m"
    assert "unless verified" in fetched.applicability


def test_find_observations_never_collapses_conflicting_observations(session):
    """Two observations for the same site and knowledge type, with different values and
    applicability, must both survive -- this schema must not force a single 'the answer'."""
    site = _make_site(session)
    session.add_all(
        [
            SurveyObservation(
                site_id=site.id,
                knowledge_type="pile_depth",
                location_description="Near Driver Room",
                description="Shallow piles observed here",
                source="Job X",
                applicability="Local to Driver Room area only",
                observed_value="<=9m",
            ),
            SurveyObservation(
                site_id=site.id,
                knowledge_type="pile_depth",
                location_description="Near Loading Dock",
                description="Deeper piles required here",
                source="Job Y",
                applicability="Local to Loading Dock area only",
                observed_value="15m",
            ),
        ]
    )
    session.commit()

    observations = find_observations(session, site.id, "pile_depth")
    assert len(observations) == 2
    assert {o.observed_value for o in observations} == {"<=9m", "15m"}


def test_find_observations_filters_by_knowledge_type(session):
    site = _make_site(session)
    session.add_all(
        [
            SurveyObservation(
                site_id=site.id, knowledge_type="pile_depth", location_description="A",
                description="d", source="s", applicability="a",
            ),
            SurveyObservation(
                site_id=site.id, knowledge_type="soil_bearing", location_description="B",
                description="d", source="s", applicability="a",
            ),
        ]
    )
    session.commit()

    pile_obs = find_observations(session, site.id, "pile_depth")
    assert len(pile_obs) == 1
    assert pile_obs[0].knowledge_type == "pile_depth"

    all_obs = find_observations(session, site.id)
    assert len(all_obs) == 2
