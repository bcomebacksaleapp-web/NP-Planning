from datetime import date

from app.core.models.identity import Permission, Role, RolePermission, User
from app.core.models.supplier import Supplier, SupplierQuote
from app.domain.auth import set_password


def _login(session, client):
    role = Role(code="PROCUREMENT", name="Procurement")
    permission = Permission(resource="supplier_quote", action_level="DRAFT")
    session.add_all([role, permission])
    session.flush()
    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    session.flush()

    user = User(email="procurement@example.com", name="Procurement", role_id=role.id)
    session.add(user)
    session.flush()
    set_password(session, user, "correct-horse-battery-staple")
    session.commit()

    return client.post(
        "/auth/login", json={"email": user.email, "password": "correct-horse-battery-staple"}
    ).json()["token"]


def _make_supplier_quote(session) -> SupplierQuote:
    supplier = Supplier(name="Supplier A")
    session.add(supplier)
    session.flush()
    quote = SupplierQuote(
        supplier_id=supplier.id, material_description="Metal Sheet", quoted_price=98.0,
        quote_date=date(2026, 1, 1), validity_days=14, lock_days=30, lead_time_days=21,
    )
    session.add(quote)
    session.commit()
    return quote


def test_create_supplier_requires_permission(session, client):
    response = client.post("/suppliers", json={"name": "Supplier A"})
    assert response.status_code == 401


def test_create_supplier_is_idempotent_on_name(session, client):
    token = _login(session, client)
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/suppliers", json={"name": "Supplier A"}, headers=headers)
    second = client.post("/suppliers", json={"name": "Supplier A"}, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_create_supplier_quote(session, client):
    token = _login(session, client)
    headers = {"Authorization": f"Bearer {token}"}

    supplier = client.post("/suppliers", json={"name": "Supplier A"}, headers=headers).json()
    response = client.post(
        "/suppliers/quotes",
        json={
            "supplier_id": supplier["id"], "material_description": "Metal Sheet", "quoted_price": 98.0,
            "quote_date": "2026-01-01", "validity_days": 14, "lock_days": 30, "lead_time_days": 21,
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["quoted_price"] == 98.0
    assert response.json()["actual_procurement_price"] is None


def test_record_actual_procurement_requires_permission(session, client):
    quote = _make_supplier_quote(session)
    response = client.post(f"/suppliers/quotes/{quote.id}/actual-procurement", json={"actual_price": 99.5, "actual_lead_time_days": 25})
    assert response.status_code == 401


def test_record_actual_procurement_fills_actuals_without_touching_quoted_fields(session, client):
    quote = _make_supplier_quote(session)
    token = _login(session, client)

    response = client.post(
        f"/suppliers/quotes/{quote.id}/actual-procurement",
        json={"actual_price": 99.5, "actual_lead_time_days": 25},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["actual_procurement_price"] == 99.5
    assert body["actual_lead_time_days"] == 25
    assert body["quoted_price"] == 98.0  # untouched
