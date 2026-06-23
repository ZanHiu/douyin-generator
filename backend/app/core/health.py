from collections.abc import Callable

from redis import Redis
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import engine


def check_database() -> tuple[bool, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "ok"
    except SQLAlchemyError as exc:
        return False, str(exc)


def check_redis() -> tuple[bool, str]:
    client: Redis | None = None
    try:
        client = Redis.from_url(settings.redis_url)
        client.ping()
        return True, "ok"
    except Exception as exc:
        return False, str(exc)
    finally:
        if client is not None:
            client.close()


def readiness_payload() -> tuple[bool, dict[str, object]]:
    checks: dict[str, Callable[[], tuple[bool, str]]] = {
        "database": check_database,
        "redis": check_redis,
    }
    payload_checks: dict[str, dict[str, str]] = {}
    ready = True

    for name, checker in checks.items():
        ok, detail = checker()
        payload_checks[name] = {
            "status": "ok" if ok else "error",
            "detail": detail,
        }
        ready = ready and ok

    return ready, {
        "status": "ok" if ready else "degraded",
        "checks": payload_checks,
    }
