from app.core.models.identity import Role, User
from app.domain.auth import set_password


def _make_user(session, email="jane@example.com", password="correct-horse-battery-staple") -> User:
    role = Role(code="ESTIMATOR", name="Estimator")
    session.add(role)
    session.flush()
    user = User(email=email, name="Jane", role_id=role.id)
    session.add(user)
    session.flush()
    set_password(session, user, password)
    session.commit()
    return user


def test_login_returns_a_token_for_valid_credentials(session, client):
    user = _make_user(session)
    response = client.post("/auth/login", json={"email": user.email, "password": "correct-horse-battery-staple"})
    assert response.status_code == 200
    assert len(response.json()["token"]) > 20


def test_login_rejects_invalid_credentials(session, client):
    user = _make_user(session)
    response = client.post("/auth/login", json={"email": user.email, "password": "wrong"})
    assert response.status_code == 401


def test_logout_revokes_the_token(session, client):
    user = _make_user(session)
    token = client.post(
        "/auth/login", json={"email": user.email, "password": "correct-horse-battery-staple"}
    ).json()["token"]

    logout_response = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_response.status_code == 204

    protected_response = client.get("/business/health", headers={"Authorization": f"Bearer {token}"})
    assert protected_response.status_code == 401
