from app.core.models.identity import Permission, Role, RolePermission, User
from app.core.models.party import Customer, Site
from app.domain.auth import set_password


def _login_with_grants(session, client, grants: list[tuple[str, str]]):
    role = Role(code="PM", name="Project Manager")
    session.add(role)
    session.flush()
    for resource, action_level in grants:
        permission = Permission(resource=resource, action_level=action_level)
        session.add(permission)
        session.flush()
        session.add(RolePermission(role_id=role.id, permission_id=permission.id))
        session.flush()

    user = User(email="pm@example.com", name="PM", role_id=role.id)
    session.add(user)
    session.flush()
    set_password(session, user, "correct-horse-battery-staple")
    session.commit()

    token = client.post(
        "/auth/login", json={"email": user.email, "password": "correct-horse-battery-staple"}
    ).json()["token"]
    return token


def _make_site(session) -> Site:
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    session.commit()
    return site


def test_site_quality_endpoints_require_permission(session, client):
    site = _make_site(session)
    assert client.get(f"/sites/{site.id}/quality").status_code == 401
    assert client.post(f"/sites/{site.id}/quality-flags", json={"flag_type": "BAD_PAYMENT", "description": "x", "flagged_by": "PM"}).status_code == 401


def test_flag_and_check_and_resolve_site_health(session, client):
    site = _make_site(session)
    token = _login_with_grants(session, client, [("site_quality_flag", "DRAFT"), ("site_quality_flag", "READ")])
    headers = {"Authorization": f"Bearer {token}"}

    initial_health = client.get(f"/sites/{site.id}/quality", headers=headers)
    assert initial_health.json()["is_healthy"] is True

    flag_response = client.post(
        f"/sites/{site.id}/quality-flags",
        json={"flag_type": "BAD_PAYMENT", "description": "60+ days late", "flagged_by": "PM K."},
        headers=headers,
    )
    assert flag_response.status_code == 200
    flag_id = flag_response.json()["id"]

    flagged_health = client.get(f"/sites/{site.id}/quality", headers=headers)
    assert flagged_health.json()["is_healthy"] is False
    assert len(flagged_health.json()["active_flags"]) == 1

    resolve_response = client.post(f"/quality-flags/{flag_id}/resolve", headers=headers)
    assert resolve_response.status_code == 200
    assert resolve_response.json()["resolved"] is True

    final_health = client.get(f"/sites/{site.id}/quality", headers=headers)
    assert final_health.json()["is_healthy"] is True
