from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.domain.auth import InvalidCredentialsError, login, revoke_session

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str


@router.post("/login", response_model=LoginResponse)
def login_route(body: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    try:
        token = login(db, body.email, body.password)
    except InvalidCredentialsError as exc:
        # A failed attempt on a real user mutates failed_login_attempts/locked_until
        # (app.domain.auth.login) via session.flush(), not session.commit() -- flush alone
        # never survives get_db's `finally: db.close()`, which rolls back whatever wasn't
        # committed. Without this commit, the lockout bookkeeping is silently discarded at the
        # end of every failed request, and the account can never actually lock. Committing here
        # is safe even when nothing was mutated (an unknown email, an inactive/archived account).
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    db.commit()
    return LoginResponse(token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_route(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme), db: Session = Depends(get_db)
) -> None:
    if credentials is not None:
        revoke_session(db, credentials.credentials)
        db.commit()
