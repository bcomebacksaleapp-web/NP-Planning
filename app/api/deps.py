from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.models.identity import User
from app.domain.auth import InvalidSessionError, resolve_session
from app.domain.authorization import has_permission

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Real session verification (app.domain.auth.resolve_session), not a placeholder that
    trusts whatever header is sent -- this is the piece Sprint 0.6's has_permission() docstring
    said was deliberately missing until real endpoints existed to protect."""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        return resolve_session(db, credentials.credentials)
    except InvalidSessionError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc


def require_permission(resource: str, action_level: str):
    """Dependency factory: raises 403 unless the current user's role has `action_level` (or
    higher) on `resource`, via Sprint 0.6's has_permission(). A role with no grant at all is
    denied by default (fails closed), not silently allowed.
    """

    def _check(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        if not has_permission(db, user.role_id, resource, action_level):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"Role lacks {action_level} on {resource!r}"
            )
        return user

    return _check
