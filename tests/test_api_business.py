from app.core.models.identity import Permission, Role, RolePermission, User
from app.domain.auth import set_password


def _login(session, client, role_code="ESTIMATOR", grant_permission=False):
    role = Role(code=role_code, name=role_code)
    session.add(role)
    session.flush()
    if grant_permission:
        permission = Permission(resource="business_health", action_level="READ")
        session.add(permission)
        session.flush()
        session.add(RolePermission(role_id=role.id, permission_id=permission.id))
        session.flush()

    user = User(email="user@example.com", name="User", role_id=role.id)
    session.add(user)
    session.flush()
    set_password(session, user, "correct-horse-battery-staple")
    session.commit()

    token = client.post("/auth/login", json={"email": user.email, "password": "correct-horse-battery-staple"}).json()[
        "token"
    ]
    return token


def test_business_health_requires_authentication(client):
    response = client.get("/business/health")
    assert response.status_code == 401


def test_business_health_denies_a_role_without_the_permission(session, client):
    token = _login(session, client, grant_permission=False)
    response = client.get("/business/health", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_business_health_returns_real_data_when_permitted(session, client):
    token = _login(session, client, grant_permission=True)
    response = client.get("/business/health", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert "pipeline_by_state" in body
    assert body["pipeline_by_state"]["DISCOVERED"] == 0  # real aggregation, just no data yet
    assert body["quote_gm_summary"]["quote_count"] == 0
