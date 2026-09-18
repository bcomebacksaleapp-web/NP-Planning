"""Real authentication -- password hashing and server-verified sessions. This is exactly the
infrastructure Sprint 0.6's has_permission() docstring said was missing: "no real endpoint to
protect yet, and a placeholder auth mechanism would look like security without being any." Now
that real endpoints exist (app/api), building the real thing instead of a placeholder is in
order.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.core.models.identity import User
from app.core.models.session_token import SessionToken

SESSION_DURATION_HOURS = 12
MAX_PASSWORD_BYTES = 72  # bcrypt silently ignores anything beyond this -- reject rather than
# accept a password that doesn't fully count, which is worse than just saying so up front.

# Brute-force protection: 3 wrong passwords in a row locks the account for LOCKOUT_MINUTES.
# Scoped per-account (not per-IP) since this is an internal staff system with a small, known
# set of accounts, not a public signup form where account enumeration via lockout messaging
# would matter the way it does for login()'s timing-attack defense below.
LOCKOUT_THRESHOLD = 3
LOCKOUT_MINUTES = 15

# A precomputed hash of a value nobody can ever type, used only to give login() something to
# bcrypt-compare against when the email doesn't match a real user (see the timing-attack note
# on login() below). Never used to authenticate anyone.
_DUMMY_HASH = bcrypt.hashpw(b"no-such-user-dummy-hash", bcrypt.gensalt()).decode()


class InvalidCredentialsError(Exception):
    pass


class InvalidSessionError(Exception):
    pass


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), password_hash.encode())


def set_password(session: Session, user: User, plain_password: str) -> None:
    if len(plain_password.encode()) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password exceeds bcrypt's {MAX_PASSWORD_BYTES}-byte limit")
    user.password_hash = hash_password(plain_password)
    session.flush()


def _hash_token(raw_token: str) -> str:
    # SHA-256 (not bcrypt) here -- the raw token is already a 32-byte cryptographically random
    # value (secrets.token_urlsafe), not a low-entropy human password, so a fast, deterministic
    # hash that also lets us index/look up by token_hash is the right tool, not a slow salted one.
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _as_aware_utc(dt: datetime) -> datetime:
    """SQLite doesn't actually preserve timezone-awareness on a DateTime(timezone=True) column
    the way Postgres does -- it stores/reads back a naive datetime, so a value round-tripped
    through SQLite compares as naive even though every value this app ever writes is UTC by
    convention (see app.core.db.utcnow). Postgres already returns an aware datetime, so this is
    a no-op there; on SQLite it restores the UTC tzinfo we know was always implied."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def login(session: Session, email: str, plain_password: str) -> str:
    """Verifies credentials and issues a new session token. Returns the RAW token -- only its
    hash is ever persisted, so this is the one moment the raw value exists in memory. Losing it
    means logging in again, not an unrecoverable session (that's the intended trade-off).

    Always runs a bcrypt comparison, even when no such user/password exists, against a fixed
    dummy hash (_DUMMY_HASH) -- short-circuiting on "user not found" without paying bcrypt's cost
    made an unknown email respond ~160x faster than a known one with a wrong password in
    practice, letting an attacker enumerate valid emails purely by timing the response. Real
    users/hashes still go through verify_password unchanged; only the "nothing to compare
    against" case gets a decoy comparison instead of skipping the work.

    Brute-force lockout: a real user's wrong-password attempts are counted on the User row
    itself; hitting LOCKOUT_THRESHOLD locks the account for LOCKOUT_MINUTES regardless of
    whether the *next* attempt would have been correct. This check runs before the bcrypt
    comparison (skip the work, we're rejecting either way) and deliberately returns a distinct
    "account locked" message -- unlike the not-found/wrong-password case above, revealing that a
    lockout is in effect is the intended, standard behavior of a lockout feature, not a leak.
    """
    user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()

    if user is not None and user.locked_until is not None and _as_aware_utc(user.locked_until) > utcnow():
        remaining_seconds = (_as_aware_utc(user.locked_until) - utcnow()).total_seconds()
        minutes = max(1, int(remaining_seconds // 60) + 1)
        raise InvalidCredentialsError(
            f"Account locked after too many failed login attempts. Try again in {minutes} minute(s)."
        )

    password_hash = user.password_hash if user is not None and user.password_hash is not None else _DUMMY_HASH
    password_ok = verify_password(plain_password, password_hash)

    if user is None or user.password_hash is None or not password_ok:
        if user is not None and user.password_hash is not None:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= LOCKOUT_THRESHOLD:
                user.locked_until = utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
                user.failed_login_attempts = 0
            session.flush()
        raise InvalidCredentialsError("Invalid email or password")
    if user.archived_at is not None:
        raise InvalidCredentialsError("Account is archived")
    if not user.is_active:
        raise InvalidCredentialsError("Account is inactive")

    # A successful login clears any accumulated failed-attempt count -- 2 wrong passwords
    # followed by the correct one is not "on the way to a lockout", it's just a typo recovered.
    user.failed_login_attempts = 0
    user.locked_until = None

    raw_token = secrets.token_urlsafe(32)
    session.add(
        SessionToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=utcnow() + timedelta(hours=SESSION_DURATION_HOURS),
        )
    )
    session.flush()
    return raw_token


def resolve_session(session: Session, raw_token: str) -> User:
    """Verifies a raw token against its stored hash and returns the current user -- real
    verification, not "trust whatever header is sent"."""
    token = session.execute(
        select(SessionToken).where(SessionToken.token_hash == _hash_token(raw_token))
    ).scalar_one_or_none()
    if token is None:
        raise InvalidSessionError("Session not found")
    if token.revoked_at is not None:
        raise InvalidSessionError("Session has been revoked")
    if _as_aware_utc(token.expires_at) < utcnow():
        raise InvalidSessionError("Session has expired")

    user = session.get(User, token.user_id)
    if user is None or user.archived_at is not None or not user.is_active:
        raise InvalidSessionError("User is no longer active")
    return user


def revoke_session(session: Session, raw_token: str) -> None:
    token = session.execute(
        select(SessionToken).where(SessionToken.token_hash == _hash_token(raw_token))
    ).scalar_one_or_none()
    if token is not None and token.revoked_at is None:
        token.revoked_at = utcnow()
        session.flush()
