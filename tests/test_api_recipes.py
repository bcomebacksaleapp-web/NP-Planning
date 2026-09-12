from app.core.models.identity import Permission, Role, RolePermission, User
from app.core.models.product import Product
from app.domain.auth import set_password


def _login(session, client):
    role = Role(code="PRODUCT_OWNER", name="Product Owner")
    permission = Permission(resource="product_recipe", action_level="DRAFT")
    session.add_all([role, permission])
    session.flush()
    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    session.flush()

    user = User(email="product@example.com", name="Product Owner", role_id=role.id)
    session.add(user)
    session.flush()
    set_password(session, user, "correct-horse-battery-staple")
    session.commit()

    return client.post(
        "/auth/login", json={"email": user.email, "password": "correct-horse-battery-staple"}
    ).json()["token"]


def _make_product(session) -> Product:
    product = Product(code="CANOPY", name="Canopy")
    session.add(product)
    session.commit()
    return product


def test_recipe_endpoints_require_permission(session, client):
    product = _make_product(session)
    response = client.post("/recipes", json={"product_id": str(product.id), "name": "Standard", "formula": {}})
    assert response.status_code == 401


def test_create_update_and_restore_recipe_version(session, client):
    product = _make_product(session)
    token = _login(session, client)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/recipes", json={"product_id": str(product.id), "name": "Standard", "formula": {"waste_factor": 0.05}},
        headers=headers,
    )
    assert create_response.status_code == 200
    assert create_response.json()["version_number"] == 1
    recipe_id = create_response.json()["recipe_id"]

    update_response = client.put(
        f"/recipes/{recipe_id}", json={"formula": {"waste_factor": 0.08}}, headers=headers
    )
    assert update_response.status_code == 200
    assert update_response.json()["version_number"] == 2

    restore_response = client.post(
        f"/recipes/{recipe_id}/restore", json={"target_version_number": 1}, headers=headers
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["version_number"] == 3
    assert restore_response.json()["formula"] == {"waste_factor": 0.05}
    assert restore_response.json()["restored_from_version_number"] == 1
