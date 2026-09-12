from app.core.models.identity import Permission, Role, RolePermission, User
from app.core.models.party import Customer, Site
from app.domain.auth import set_password
from app.domain.pricing import selling_price_for_gm30
from app.domain.projects import create_project
from app.domain.quotes import create_quote


def _login(session, client, action_level="READ"):
    role = Role(code="MANAGEMENT", name="Management")
    permission = Permission(resource="quote", action_level=action_level)
    session.add_all([role, permission])
    session.flush()
    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    session.flush()

    user = User(email="mgmt@example.com", name="Management", role_id=role.id)
    session.add(user)
    session.flush()
    set_password(session, user, "correct-horse-battery-staple")
    session.commit()

    return client.post(
        "/auth/login", json={"email": user.email, "password": "correct-horse-battery-staple"}
    ).json()["token"]


def _make_quote(session, gm_percent):
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    project = create_project(session, site.id, {})
    cost = 100_000
    price = cost / (1 - gm_percent / 100)
    quote = create_quote(session, project.id, cost, price, [{"description": "x", "quantity": 1, "unit_price": price}])
    session.commit()
    return quote


def test_what_if_requires_exactly_one_scenario_field(session, client):
    quote = _make_quote(session, 35.0)
    token = _login(session, client)
    headers = {"Authorization": f"Bearer {token}"}

    neither = client.post(f"/quotes/{quote.id}/what-if", json={}, headers=headers)
    assert neither.status_code == 400

    both = client.post(
        f"/quotes/{quote.id}/what-if", json={"cost_change_percent": 8.0, "discount_percent": 5.0}, headers=headers
    )
    assert both.status_code == 400


def test_what_if_cost_increase_matches_the_blueprints_example(session, client):
    quote = _make_quote(session, 30.0)  # exactly at GM30 pass floor
    token = _login(session, client)

    response = client.post(
        f"/quotes/{quote.id}/what-if",
        json={"cost_change_percent": 8.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["hypothetical_true_cost"] == 108_000
    assert body["gate_status"] != "PASS"


def test_recommendations_reflect_the_quotes_actual_gate_status(session, client):
    quote = _make_quote(session, 10.0)  # BLOCKED
    token = _login(session, client)

    response = client.get(f"/quotes/{quote.id}/recommendations", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    actions = response.json()
    assert len(actions) == 1
    assert "blocked" in actions[0]["issue"].lower()
    assert actions[0]["allowed_next_action"] in ("READ", "SUGGEST", "DRAFT")


def test_recommendations_empty_for_a_passing_quote(session, client):
    quote = _make_quote(session, 35.0)
    token = _login(session, client)

    response = client.get(f"/quotes/{quote.id}/recommendations", headers={"Authorization": f"Bearer {token}"})
    assert response.json() == []
