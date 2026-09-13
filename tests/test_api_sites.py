from app.core.models.identity import Permission, Role, RolePermission, User
from app.core.models.party import Customer
from app.domain.auth import set_password


def _login(session, client):
    role = Role(code="SITE_ENGINEER", name="Site Engineer")
    permission = Permission(resource="site", action_level="DRAFT")
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


def test_create_site_requires_permission(session, client):
    response = client.post(
        "/sites", json={"customer_name": "Test Customer", "site_type": "HOME", "name": "Test Site"}
    )
    assert response.status_code == 401


def test_create_site_gets_or_creates_customer_by_name(session, client):
    token = _login(session, client)
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post(
        "/sites", json={"customer_name": "Test Customer", "site_type": "HOME", "name": "Site A"},
        headers=headers,
    )
    second = client.post(
        "/sites", json={"customer_name": "Test Customer", "site_type": "OFFICE", "name": "Site B"},
        headers=headers,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["customer_id"] == second.json()["customer_id"]
    assert session.query(Customer).filter_by(name="Test Customer").count() == 1


def test_create_site_rejects_invalid_site_type(session, client):
    token = _login(session, client)
    response = client.post(
        "/sites", json={"customer_name": "Test Customer", "site_type": "SPACESHIP", "name": "Site A"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
