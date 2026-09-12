import pytest

from app.core.models.identity import Role, User
from app.domain.auth import (
    InvalidCredentialsError,
    InvalidSessionError,
    login,
    resolve_session,
    revoke_session,
    set_password,
)


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


def test_login_succeeds_with_correct_password(session):
    user = _make_user(session)
    token = login(session, user.email, "correct-horse-battery-staple")
    assert isinstance(token, str)
    assert len(token) > 20


def test_login_fails_with_wrong_password(session):
    user = _make_user(session)
    with pytest.raises(InvalidCredentialsError):
        login(session, user.email, "wrong-password")


def test_login_fails_with_unknown_email(session):
    with pytest.raises(InvalidCredentialsError):
        login(session, "nobody@example.com", "whatever")


def test_login_fails_for_a_user_with_no_password_set(session):
    role = Role(code="ESTIMATOR", name="Estimator")
    session.add(role)
    session.flush()
    user = User(email="nopass@example.com", name="No Password", role_id=role.id)
    session.add(user)
    session.commit()

    with pytest.raises(InvalidCredentialsError):
        login(session, user.email, "anything")


def test_login_fails_for_an_archived_user(session):
    from app.domain.archiving import archive

    user = _make_user(session)
    archive(session, user)
    session.commit()

    with pytest.raises(InvalidCredentialsError):
        login(session, user.email, "correct-horse-battery-staple")


def test_resolve_session_returns_the_logged_in_user(session):
    user = _make_user(session)
    token = login(session, user.email, "correct-horse-battery-staple")
    session.commit()

    resolved = resolve_session(session, token)
    assert resolved.id == user.id


def test_resolve_session_rejects_an_unknown_token(session):
    with pytest.raises(InvalidSessionError):
        resolve_session(session, "not-a-real-token")


def test_revoked_session_can_no_longer_be_resolved(session):
    user = _make_user(session)
    token = login(session, user.email, "correct-horse-battery-staple")
    session.commit()

    revoke_session(session, token)
    session.commit()

    with pytest.raises(InvalidSessionError):
        resolve_session(session, token)


def test_password_hash_is_never_the_plain_password(session):
    user = _make_user(session, password="my-real-password")
    assert user.password_hash != "my-real-password"
    assert "my-real-password" not in user.password_hash


def test_login_takes_the_same_time_for_unknown_email_as_wrong_password(session):
    """Locks in the timing-attack fix: an unknown email must not respond fast enough to be
    distinguishable from a known email with a wrong password (161x difference before the fix,
    a trivial enumeration oracle for an attacker timing responses)."""
    import time

    _make_user(session)

    t0 = time.perf_counter()
    with pytest.raises(InvalidCredentialsError):
        login(session, "unknown@example.com", "whatever")
    unknown_duration = time.perf_counter() - t0

    t0 = time.perf_counter()
    with pytest.raises(InvalidCredentialsError):
        login(session, "jane@example.com", "wrong-password")
    known_duration = time.perf_counter() - t0

    # Both paths now run a real bcrypt comparison -- allow generous slack for CI jitter, but a
    # regression back to short-circuiting would reliably blow well past 3x, not hover near 1x.
    assert known_duration / unknown_duration < 3.0


def test_login_rejects_an_inactive_user(session):
    """User.is_active existed but was never enforced anywhere in the auth flow -- a user marked
    inactive (but not archived) could still log in. Fixed; locked in here."""
    user = _make_user(session)
    user.is_active = False
    session.commit()

    with pytest.raises(InvalidCredentialsError):
        login(session, user.email, "correct-horse-battery-staple")


def test_resolve_session_rejects_a_user_deactivated_after_login(session):
    user = _make_user(session)
    token = login(session, user.email, "correct-horse-battery-staple")
    session.commit()

    user.is_active = False
    session.commit()

    with pytest.raises(InvalidSessionError):
        resolve_session(session, token)


def test_set_password_rejects_passwords_bcrypt_would_silently_truncate(session):
    role = Role(code="ESTIMATOR", name="Estimator")
    session.add(role)
    session.flush()
    user = User(email="longpw@example.com", name="Long", role_id=role.id)
    session.add(user)
    session.flush()

    with pytest.raises(ValueError):
        set_password(session, user, "a" * 73)


def test_expired_session_is_rejected(session):
    """Locks in the timezone-comparison fix: SQLite returns a naive datetime for
    expires_at even though it was written as UTC-aware, and comparing that against a fresh
    aware utcnow() must not silently treat every session as non-expired (or crash)."""
    from datetime import datetime, timezone

    from app.core.models.session_token import SessionToken
    from app.domain.auth import _hash_token

    user = _make_user(session)
    raw_token = "already-expired-token"
    session.add(
        SessionToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
    )
    session.commit()

    with pytest.raises(InvalidSessionError):
        resolve_session(session, raw_token)
