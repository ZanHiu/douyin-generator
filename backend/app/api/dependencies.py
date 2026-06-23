from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.services.auth_service import AuthService


def require_authenticated_user(
    auth_token: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
    db: Session = Depends(get_db),
) -> User:
    user = AuthService(db).get_user_by_session_token(auth_token or "")
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user
