from app.core.models.identity import Permission, Role, RolePermission, User
from app.core.models.product import Product
from app.domain.auth import set_password


def _login(session, client):
    role = Role(code="ESTIMATOR", name="Estimator")
    permission = Permission(resource="product_recipe", action_level="READ")
    session.add_all([role, permission])
    session.flush()
    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    session.flush()

    user = User(email="estimator@example.com", name="Estimator", role_id=role.id)
    session.add(user)
    session.flush()
    set_password(session, user, "correct-horse-battery-staple")
    session.commit()

    return client.post(
        "/auth/login", json={"email": user.email, "password": "correct-horse-battery-staple"}
    ).json()["token"]


def test_list_products_requires_permission(client):
    assert client.get("/products").status_code == 401


def test_list_products_returns_real_products(session, client):
    session.add(Product(code="CANOPY", name="Canopy"))
    session.commit()
    token = _login(session, client)

    response = client.get("/products", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    codes = [p["code"] for p in response.json()]
    assert "CANOPY" in codes
