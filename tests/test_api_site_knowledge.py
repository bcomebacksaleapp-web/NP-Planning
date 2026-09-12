from app.core.models.identity import Permission, Role, RolePermission, User
from app.core.models.party import Customer, Site
from app.core.models.survey import SurveyObservation
from app.domain.auth import set_password


def _login(session, client):
    role = Role(code="SITE_ENGINEER", name="Site Engineer")
    permission = Permission(resource="site_knowledge", action_level="READ")
    session.add_all([role, permission])
    session.flush()
    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    session.flush()

    user = User(email="engineer@example.com", name="Engineer", role_id=role.id)
    session.add(user)
    session.flush()
    set_password(session, user, "correct-horse-battery-staple")
    session.commit()

    return client.post(
        "/auth/login", json={"email": user.email, "password": "correct-horse-battery-staple"}
    ).json()["token"]


def _make_site(session) -> Site:
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    return site


def test_site_knowledge_requires_permission(session, client):
    site = _make_site(session)
    assert client.get(f"/sites/{site.id}/knowledge").status_code == 401


def test_site_knowledge_returns_observations(session, client):
    site = _make_site(session)
    session.add(
        SurveyObservation(
            site_id=site.id, knowledge_type="pile_depth", location_description="Near Driver Room",
            description="Observed during excavation", source="Job X", applicability="local",
            verified_by="Engineer P.",
        )
    )
    session.commit()
    token = _login(session, client)

    response = client.get(f"/sites/{site.id}/knowledge", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["verified_by"] == "Engineer P."


def test_survey_checklist_classifies_each_type(session, client):
    site = _make_site(session)
    session.add(
        SurveyObservation(
            site_id=site.id, knowledge_type="pile_depth", location_description="A",
            description="d", source="s", applicability="a", verified_by="Engineer",
        )
    )
    session.commit()
    token = _login(session, client)

    response = client.get(
        f"/sites/{site.id}/survey-checklist?knowledge_types=pile_depth,soil_bearing",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"pile_depth": "KNOWN", "soil_bearing": "UNKNOWN"}
