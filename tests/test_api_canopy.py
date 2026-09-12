from app.core.models.identity import Permission, Role, RolePermission, User
from app.core.models.party import Customer, Site
from app.domain.auth import set_password


def _login_with_grant(session, client, resource, action_level, role_code="ESTIMATOR"):
    role = Role(code=role_code, name=role_code)
    permission = Permission(resource=resource, action_level=action_level)
    session.add_all([role, permission])
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


def test_configure_canopy_requires_draft_permission(session, client):
    site = _make_site(session)
    response = client.post(
        "/canopy/configure",
        json={"site_id": str(site.id), "width_m": 6.0, "length_m": 4.0, "roof_cover": "Metal Sheet", "unit_cost_per_m2": 1500.0},
    )
    assert response.status_code == 401  # no token at all


def test_configure_canopy_creates_a_real_quote(session, client):
    site = _make_site(session)
    _, token = _login_with_grant(session, client, "quote", "DRAFT")

    response = client.post(
        "/canopy/configure",
        json={"site_id": str(site.id), "width_m": 6.0, "length_m": 4.0, "roof_cover": "Metal Sheet", "unit_cost_per_m2": 1500.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["gate_status"] == "OVERRIDE_REQUIRED"  # C3: placeholder quantity basis
    assert body["project_id"]
    assert body["quote_id"]


def test_confirm_quote_requires_commit_permission_not_draft(session, client):
    """A role with only DRAFT on quote must not be able to confirm -- COMMIT is a stronger
    permission (Sprint 0.6's has_permission ordering), and confirming is Law 14's COMMIT-level
    action, distinct from configuring."""
    site = _make_site(session)
    _, draft_token = _login_with_grant(session, client, "quote", "DRAFT")

    configure_response = client.post(
        "/canopy/configure",
        json={"site_id": str(site.id), "width_m": 6.0, "length_m": 4.0, "roof_cover": "Metal Sheet", "unit_cost_per_m2": 1500.0},
        headers={"Authorization": f"Bearer {draft_token}"},
    )
    ids = configure_response.json()

    confirm_response = client.post(
        "/quotes/confirm",
        json={"project_id": ids["project_id"], "quote_id": ids["quote_id"], "confirmed_by": "Estimator J."},
        headers={"Authorization": f"Bearer {draft_token}"},
    )
    assert confirm_response.status_code == 403


def test_confirm_quote_with_commit_permission_and_override_reason_succeeds(session, client):
    site = _make_site(session)
    _, draft_token = _login_with_grant(session, client, "quote", "DRAFT", role_code="ESTIMATOR")
    _, commit_token = _login_with_grant(session, client, "quote", "COMMIT", role_code="OWNERADMIN")

    configure_response = client.post(
        "/canopy/configure",
        json={"site_id": str(site.id), "width_m": 6.0, "length_m": 4.0, "roof_cover": "Metal Sheet", "unit_cost_per_m2": 1500.0},
        headers={"Authorization": f"Bearer {draft_token}"},
    )
    ids = configure_response.json()

    # gate_status is OVERRIDE_REQUIRED (C3 placeholder quantity) -- confirming without a reason
    # must be refused.
    no_reason_response = client.post(
        "/quotes/confirm",
        json={"project_id": ids["project_id"], "quote_id": ids["quote_id"], "confirmed_by": "Owner K."},
        headers={"Authorization": f"Bearer {commit_token}"},
    )
    assert no_reason_response.status_code == 400

    with_reason_response = client.post(
        "/quotes/confirm",
        json={
            "project_id": ids["project_id"], "quote_id": ids["quote_id"], "confirmed_by": "Owner K.",
            "override_reason": "Placeholder formula acceptable for this pilot customer",
        },
        headers={"Authorization": f"Bearer {commit_token}"},
    )
    assert with_reason_response.status_code == 200
    assert with_reason_response.json()["project_state"] == "CONFIRMED"
