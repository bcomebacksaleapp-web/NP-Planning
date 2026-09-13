from app.core.models.critical_spec import CriticalSpec
from app.core.models.identity import Permission, Role, RolePermission, User
from app.core.models.party import Customer, Site
from app.domain.auth import set_password
from app.domain.projects import create_project


def _login_with_grant(session, client, resource, action_level):
    role = Role(code="ESTIMATOR", name="Estimator")
    permission = Permission(resource=resource, action_level=action_level)
    session.add_all([role, permission])
    session.flush()
    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    session.flush()

    user = User(email="estimator@example.com", name="Estimator", role_id=role.id)
    session.add(user)
    session.flush()
    set_password(session, user, "correct-horse-battery-staple")
    session.commit()

    token = client.post(
        "/auth/login", json={"email": user.email, "password": "correct-horse-battery-staple"}
    ).json()["token"]
    return token


def _make_spec(session) -> CriticalSpec:
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    project = create_project(session, site.id, {})
    spec = CriticalSpec(project_id=project.id, spec_type="roof_material_model", description="TBD")
    session.add(spec)
    session.commit()
    return spec


def _make_project(session):
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    return create_project(session, site.id, {})


def test_create_requires_permission(session, client):
    project = _make_project(session)
    response = client.post(
        "/critical-specs", json={"project_id": str(project.id), "spec_type": "roof_material_model", "description": "TBD"}
    )
    assert response.status_code == 401


def test_create_critical_spec_starts_in_discussion(session, client):
    project = _make_project(session)
    token = _login_with_grant(session, client, "critical_spec", "DRAFT")

    response = client.post(
        "/critical-specs",
        json={"project_id": str(project.id), "spec_type": "roof_material_model", "description": "TN Polycarbonate"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "DISCUSSION"


def test_transition_requires_permission(session, client):
    spec = _make_spec(session)
    response = client.post(f"/critical-specs/{spec.id}/transition", json={"to_state": "PROPOSED"})
    assert response.status_code == 401


def test_valid_transition_succeeds(session, client):
    spec = _make_spec(session)
    token = _login_with_grant(session, client, "critical_spec", "DRAFT")

    response = client.post(
        f"/critical-specs/{spec.id}/transition",
        json={"to_state": "PROPOSED"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "PROPOSED"


def test_invalid_transition_returns_409(session, client):
    spec = _make_spec(session)
    token = _login_with_grant(session, client, "critical_spec", "DRAFT")

    response = client.post(
        f"/critical-specs/{spec.id}/transition",
        json={"to_state": "CONFIRMED"},  # skipping PROPOSED
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409


def test_confirming_records_confirmed_by(session, client):
    spec = _make_spec(session)
    token = _login_with_grant(session, client, "critical_spec", "DRAFT")
    headers = {"Authorization": f"Bearer {token}"}

    client.post(f"/critical-specs/{spec.id}/transition", json={"to_state": "PROPOSED"}, headers=headers)
    response = client.post(
        f"/critical-specs/{spec.id}/transition",
        json={"to_state": "CONFIRMED", "confirmed_by": "Estimator J."},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["confirmed_by"] == "Estimator J."
