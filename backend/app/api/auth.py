from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.auth import AuthSessionResponse, AuthUserResponse, LoginRequest
from app.services.auth_service import AuthService
from app.api.dependencies import require_authenticated_user
from app.models import User

router = APIRouter()


def _write_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=int(settings.auth_session_hours * 3600),
        httponly=True,
        samesite=settings.auth_cookie_samesite,
        secure=settings.auth_cookie_secure,
        domain=settings.auth_cookie_domain,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
        secure=settings.auth_cookie_secure,
        domain=settings.auth_cookie_domain,
        path="/",
    )


def _serialize_user(user: User) -> AuthUserResponse:
    return AuthUserResponse(id=user.id, email=user.email, is_admin=user.is_admin)


@router.post("/login", response_model=AuthSessionResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthSessionResponse:
    service = AuthService(db)
    user = service.authenticate_user(payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    _, token = service.create_session(user)
    _write_auth_cookie(response, token)
    return AuthSessionResponse(user=_serialize_user(user))


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    auth_token: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
    db: Session = Depends(get_db),
) -> Response:
    AuthService(db).revoke_session(auth_token or "")
    _clear_auth_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=AuthSessionResponse)
def me(user: User = Depends(require_authenticated_user)) -> AuthSessionResponse:
    return AuthSessionResponse(user=_serialize_user(user))
