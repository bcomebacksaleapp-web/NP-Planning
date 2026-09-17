from app.core.models.identity import Permission, Role, RolePermission, User
from app.domain.auth import set_password


def _login(session, client, action_level="READ", email="marketing2@example.com"):
    role = Role(code="MARKETING-" + action_level, name="Marketing")
    permission = Permission(resource="website_inquiry", action_level=action_level)
    session.add_all([role, permission])
    session.flush()
    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    session.flush()

    user = User(email=email, name="Marketing", role_id=role.id)
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


def test_convert_inquiry_requires_no_auth_401(client):
    inquiry_id = client.post("/inquiries", json={"name": "Somchai"}).json()["id"]
    response = client.post(
        f"/inquiries/{inquiry_id}/convert",
        json={"customer_name": "Somchai", "site_type": "FACTORY", "site_name": "Somchai Factory"},
    )
    assert response.status_code == 401


def test_convert_inquiry_requires_draft_not_just_read(session, client):
    inquiry_id = client.post("/inquiries", json={"name": "Somchai"}).json()["id"]
    token = _login(session, client, "READ")
    response = client.post(
        f"/inquiries/{inquiry_id}/convert",
        json={"customer_name": "Somchai", "site_type": "FACTORY", "site_name": "Somchai Factory"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_convert_inquiry_creates_customer_site_opportunity(session, client):
    inquiry_id = client.post(
        "/inquiries",
        json={
            "name": "Somchai", "phone": "081-234-5678", "service_interest": "Metal roofing",
            "message": "Need a quote for a 500 sqm factory roof",
        },
    ).json()["id"]
    token = _login(session, client, "DRAFT")

    response = client.post(
        f"/inquiries/{inquiry_id}/convert",
        json={
            "customer_name": "Somchai Manufacturing Co.", "site_type": "FACTORY",
            "site_name": "Somchai Factory - Rayong", "site_address": "123 Industrial Rd, Rayong",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["customer_id"] and body["site_id"] and body["opportunity_id"]
    assert body["inquiry"]["converted_to_opportunity_id"] == body["opportunity_id"]

    # The inquiry itself now reflects the conversion when re-listed.
    listed = client.get("/inquiries", headers={"Authorization": f"Bearer {token}"}).json()
    converted = next(i for i in listed if i["id"] == inquiry_id)
    assert converted["converted_to_opportunity_id"] == body["opportunity_id"]


def test_convert_inquiry_rejects_unknown_site_type(session, client):
    inquiry_id = client.post("/inquiries", json={"name": "Somchai"}).json()["id"]
    token = _login(session, client, "DRAFT")

    response = client.post(
        f"/inquiries/{inquiry_id}/convert",
        json={"customer_name": "Somchai", "site_type": "SPACESHIP", "site_name": "Somchai Site"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_convert_inquiry_404_when_missing(session, client):
    token = _login(session, client, "DRAFT")
    response = client.post(
        "/inquiries/00000000-0000-0000-0000-000000000000/convert",
        json={"customer_name": "Somchai", "site_type": "FACTORY", "site_name": "Somchai Site"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_convert_inquiry_twice_conflicts(session, client):
    inquiry_id = client.post("/inquiries", json={"name": "Somchai"}).json()["id"]
    token = _login(session, client, "DRAFT")
    headers = {"Authorization": f"Bearer {token}"}
    body = {"customer_name": "Somchai", "site_type": "FACTORY", "site_name": "Somchai Site"}

    first = client.post(f"/inquiries/{inquiry_id}/convert", json=body, headers=headers)
    assert first.status_code == 200

    second = client.post(f"/inquiries/{inquiry_id}/convert", json=body, headers=headers)
    assert second.status_code == 409


def test_convert_inquiry_reuses_existing_customer_by_name(session, client):
    first_id = client.post("/inquiries", json={"name": "Somchai"}).json()["id"]
    second_id = client.post("/inquiries", json={"name": "Somchai again"}).json()["id"]
    token = _login(session, client, "DRAFT")
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post(
        f"/inquiries/{first_id}/convert",
        json={"customer_name": "Somchai Manufacturing Co.", "site_type": "FACTORY", "site_name": "Site A"},
        headers=headers,
    ).json()
    second = client.post(
        f"/inquiries/{second_id}/convert",
        json={"customer_name": "Somchai Manufacturing Co.", "site_type": "OFFICE", "site_name": "Site B"},
        headers=headers,
    ).json()

    assert first["customer_id"] == second["customer_id"]
    assert first["site_id"] != second["site_id"]
