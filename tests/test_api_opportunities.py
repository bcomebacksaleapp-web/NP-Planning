from app.core.models.identity import Permission, Role, RolePermission, User
from app.core.models.party import Customer, Site
from app.domain.auth import set_password


def _login_with_grants(session, client, grants: list[tuple[str, str]], role_code="STAFF"):
    role = Role(code=role_code, name=role_code)
    session.add(role)
    session.flush()
    for resource, action_level in grants:
        permission = Permission(resource=resource, action_level=action_level)
        session.add(permission)
        session.flush()
        session.add(RolePermission(role_id=role.id, permission_id=permission.id))
        session.flush()

    user = User(email=f"{role_code.lower()}@example.com", name=role_code, role_id=role.id)
    session.add(user)
    session.flush()
    set_password(session, user, "correct-horse-battery-staple")
    session.commit()

    token = client.post("/auth/login", json={"email": user.email, "password": "correct-horse-battery-staple"}).json()[
        "token"
    ]
    return user, token


def _make_site(session) -> Site:
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    session.commit()
    return site


def test_create_opportunity_requires_permission(session, client):
    site = _make_site(session)
    response = client.post("/opportunities", json={"site_id": str(site.id), "source": "website_inquiry"})
    assert response.status_code == 401


def test_create_and_convert_opportunity(session, client):
    site = _make_site(session)
    _, token = _login_with_grants(session, client, [("opportunity", "DRAFT"), ("project", "DRAFT")])
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/opportunities", json={"site_id": str(site.id), "source": "referral"}, headers=headers
    )
    assert create_response.status_code == 200
    opportunity_id = create_response.json()["id"]

    convert_response = client.post(
        f"/opportunities/{opportunity_id}/convert", json={"project_data": {"name": "New Canopy"}}, headers=headers
    )
    assert convert_response.status_code == 200
    assert convert_response.json()["project_state"] == "DISCOVERED"


def test_convert_missing_opportunity_returns_404(session, client):
    _, token = _login_with_grants(session, client, [("project", "DRAFT")])
    response = client.post(
        "/opportunities/00000000-0000-0000-0000-000000000000/convert",
        json={"project_data": {}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
