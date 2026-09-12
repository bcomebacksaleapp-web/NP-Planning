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


class InvalidCredentialsError(Exception):
    pass


class InvalidSessionError(Exception):
    pass


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), password_hash.encode())


def set_password(session: Session, user: User, plain_password: str) -> None:
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
    """
    user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or user.password_hash is None or not verify_password(plain_password, user.password_hash):
        raise InvalidCredentialsError("Invalid email or password")
    if user.archived_at is not None:
        raise InvalidCredentialsError("Account is archived")

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
    if user is None or user.archived_at is not None:
        raise InvalidSessionError("User is no longer active")
    return user


def revoke_session(session: Session, raw_token: str) -> None:
    token = session.execute(
        select(SessionToken).where(SessionToken.token_hash == _hash_token(raw_token))
    ).scalar_one_or_none()
    if token is not None and token.revoked_at is None:
        token.revoked_at = utcnow()
        session.flush()
