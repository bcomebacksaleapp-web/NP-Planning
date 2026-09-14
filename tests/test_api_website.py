from app.core.models.identity import Permission, Role, RolePermission, User
from app.domain.auth import set_password


def _login(session, client):
    role = Role(code="MARKETING", name="Marketing")
    permission = Permission(resource="website_page", action_level="DRAFT")
    session.add_all([role, permission])
    session.flush()
    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    session.flush()

    user = User(email="marketing@example.com", name="Marketing", role_id=role.id)
    session.add(user)
    session.flush()
    set_password(session, user, "correct-horse-battery-staple")
    session.commit()

    return client.post(
        "/auth/login", json={"email": user.email, "password": "correct-horse-battery-staple"}
    ).json()["token"]


def test_website_endpoints_require_permission(client):
    assert client.post("/website/branches", json={"name": "MAIN"}).status_code == 401


def test_create_branch_and_page_and_update_and_restore(session, client):
    token = _login(session, client)
    headers = {"Authorization": f"Bearer {token}"}

    branch_response = client.post("/website/branches", json={"name": "MAIN"}, headers=headers)
    assert branch_response.status_code == 200
    branch_id = branch_response.json()["id"]

    page_response = client.post(
        "/website/pages",
        json={
            "branch_id": branch_id, "slug": "home",
            "widgets": [{"widget_type": "Hero", "order_index": 0, "config": {"title": "Build a better tomorrow"}}],
        },
        headers=headers,
    )
    assert page_response.status_code == 200
    assert page_response.json()["revision_number"] == 1
    assert [w["widget_type"] for w in page_response.json()["widgets"]] == ["Hero"]
    assert page_response.json()["widgets"][0]["config"] == {"title": "Build a better tomorrow"}

    page_id = page_response.json()["page_id"]
    update_response = client.put(
        f"/website/pages/{page_id}",
        json={"widgets": [{"widget_type": "ServiceCards", "order_index": 0}]},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["revision_number"] == 2

    restore_response = client.post(
        f"/website/pages/{page_id}/restore", json={"target_revision_number": 1}, headers=headers
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["revision_number"] == 3
    assert restore_response.json()["widgets"][0]["widget_type"] == "Hero"
    assert restore_response.json()["restored_from_revision_number"] == 1


def test_get_published_page_requires_no_auth_and_returns_current_revision(session, client):
    token = _login(session, client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/website/branches", json={"name": "MAIN"}, headers=headers)
    client.post(
        "/website/pages",
        json={
            "branch_id": client.post("/website/branches", json={"name": "MAIN2"}, headers=headers).json()["id"],
            "slug": "home", "widgets": [{"widget_type": "Hero", "order_index": 0, "config": {"title": "Hi"}}],
        },
        headers=headers,
    )

    response = client.get("/website/pages/MAIN2/home")
    assert response.status_code == 200
    assert response.json()["widgets"][0]["config"] == {"title": "Hi"}


def test_get_published_page_404_when_missing(client):
    assert client.get("/website/pages/NOSUCH/home").status_code == 404


def test_list_pages_requires_permission(client):
    assert client.get("/website/branches/MAIN/pages").status_code == 401


def test_list_pages_returns_slugs_for_branch(session, client):
    token = _login(session, client)
    headers = {"Authorization": f"Bearer {token}"}
    branch_id = client.post("/website/branches", json={"name": "LISTME"}, headers=headers).json()["id"]
    client.post(
        "/website/pages",
        json={"branch_id": branch_id, "slug": "home", "widgets": [{"widget_type": "Hero", "order_index": 0}]},
        headers=headers,
    )
    client.post(
        "/website/pages",
        json={"branch_id": branch_id, "slug": "about", "widgets": [{"widget_type": "Prose", "order_index": 0}]},
        headers=headers,
    )

    response = client.get("/website/branches/LISTME/pages", headers=headers)
    assert response.status_code == 200
    assert sorted(p["slug"] for p in response.json()) == ["about", "home"]
