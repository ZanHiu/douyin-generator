import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AuthSession, User
from app.services.user_settings_service import UserSettingsService


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ensure_admin_user(self) -> User | None:
        email = settings.admin_email.strip().lower()
        password = settings.admin_password
        if not email or not password:
            return None

        user = self.get_user_by_email(email)
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(password),
                is_active=True,
                is_admin=True,
                settings_json=default_user_settings().model_dump(),
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user

        changed = False
        if not verify_password(password, user.password_hash):
            user.password_hash = hash_password(password)
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if not user.is_admin:
            user.is_admin = True
            changed = True
        if changed:
            self.db.commit()
            self.db.refresh(user)
        if not isinstance(user.settings_json, dict):
            user.settings_json = default_user_settings().model_dump()
            self.db.commit()
            self.db.refresh(user)
        return user

    def authenticate_user(self, email: str, password: str) -> User | None:
        user = self.get_user_by_email(email)
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def create_session(self, user: User) -> tuple[AuthSession, str]:
        self.delete_expired_sessions()
        token = secrets.token_urlsafe(32)
        session = AuthSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=datetime.now(UTC) + timedelta(hours=settings.auth_session_hours),
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session, token

    def get_user_by_session_token(self, token: str) -> User | None:
        if not token:
            return None
        session = (
            self.db.query(AuthSession)
            .filter(AuthSession.token_hash == hash_session_token(token))
            .first()
        )
        if session is None:
            return None
        if session.expires_at <= datetime.now(UTC):
            self.db.delete(session)
            self.db.commit()
            return None
        user = session.user
        if user is None or not user.is_active:
            return None
        return user

    def revoke_session(self, token: str) -> None:
        if not token:
            return
        session = (
            self.db.query(AuthSession)
            .filter(AuthSession.token_hash == hash_session_token(token))
            .first()
        )
        if session is None:
            return
        self.db.delete(session)
        self.db.commit()

    def delete_expired_sessions(self) -> None:
        now = datetime.now(UTC)
        self.db.query(AuthSession).filter(AuthSession.expires_at <= now).delete()
        self.db.commit()

    def get_user_by_email(self, email: str) -> User | None:
        normalized = email.strip().lower()
        return self.db.query(User).filter(User.email == normalized).first()


def hash_password(password: str) -> str:
    iterations = 390000
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()
    return hmac.compare_digest(actual, expected)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def default_user_settings():
    return UserSettingsService.default_settings()
