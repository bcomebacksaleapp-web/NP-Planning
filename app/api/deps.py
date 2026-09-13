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

    KNOWN LIMITATION -- no row-level/tenant authorization: this checks permission by resource
    TYPE only ("does this role have DRAFT on 'quote'"), never by WHICH specific record. A user
    whose role grants quote:DRAFT can configure a canopy against any Site UUID in the database,
    not just ones they're associated with; a user with quote:COMMIT can confirm any customer's
    quote. This is fine for the internal-staff roles this system has been built and tested
    against so far (estimators/PMs/owners legitimately need company-wide visibility), but Part
    24 lists CUSTOMER as a role, and Part 12 describes a real customer portal ("My Home/My
    Office/My Factory") -- if a CUSTOMER-role user is ever given even a minimal READ grant so
    that portal can show their own site, the SAME grant currently lets them read or act on every
    OTHER customer's data too, since nothing here checks record ownership.

    Do not wire a CUSTOMER-role login into any real customer-facing flow until this is
    addressed (a User->Customer link plus a per-record ownership check retrofitted onto every
    site/project/quote endpoint) -- deliberately not built speculatively; this is real design
    work with modeling choices that need a real decision, not a guess made silently here.
    """

    def _check(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        if not has_permission(db, user.role_id, resource, action_level):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"Role lacks {action_level} on {resource!r}"
            )
        return user

    return _check
