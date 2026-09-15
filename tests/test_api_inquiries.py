from app.core.models.identity import Permission, Role, RolePermission, User
from app.domain.auth import set_password


def _login(session, client):
    role = Role(code="MARKETING", name="Marketing")
    permission = Permission(resource="website_inquiry", action_level="READ")
    session.add_all([role, permission])
    session.flush()
    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    session.flush()

    user = User(email="marketing2@example.com", name="Marketing", role_id=role.id)
    session.add(user)
    session.flush()
    set_password(session, user, "correct-horse-battery-staple")
    session.commit()

    return client.post(
        "/auth/login", json={"email": user.email, "password": "correct-horse-battery-staple"}
    ).json()["token"]


def test_create_inquiry_requires_no_auth(client):
    response = client.post("/inquiries", json={"name": "Somchai", "phone": "081-234-5678"})
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Somchai"
    assert body["converted_to_opportunity_id"] is None
    assert body["created_at"]


def test_create_inquiry_accepts_full_form(client):
    response = client.post(
        "/inquiries",
        json={
            "name": "Somchai", "phone": "081-234-5678", "email": "somchai@example.com",
            "service_interest": "Metal roofing", "message": "Need a quote for a 500 sqm factory roof",
            "source_page": "contact",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "somchai@example.com"
    assert body["source_page"] == "contact"


def test_list_inquiries_requires_permission(client):
    client.post("/inquiries", json={"name": "Somchai"})
    assert client.get("/inquiries").status_code == 401


def test_list_inquiries_returns_newest_first(session, client):
    client.post("/inquiries", json={"name": "First"})
    client.post("/inquiries", json={"name": "Second"})
    token = _login(session, client)

    response = client.get("/inquiries", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    names = [i["name"] for i in response.json()]
    assert names.index("Second") < names.index("First")
