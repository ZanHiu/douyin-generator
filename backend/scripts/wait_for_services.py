import sys
import time

from app.core.health import check_database, check_redis


def wait_for(check_name: str, checker, attempts: int, sleep_seconds: float) -> None:
    last_detail = "unknown error"
    for _ in range(attempts):
        ok, detail = checker()
        if ok:
            print(f"{check_name} ready")
            return
        last_detail = detail
        print(f"waiting for {check_name}: {detail}")
        time.sleep(sleep_seconds)
    raise RuntimeError(f"{check_name} not ready after {attempts} attempts: {last_detail}")


def main() -> int:
    attempts = 60
    sleep_seconds = 2.0
    wait_for("database", check_database, attempts, sleep_seconds)
    wait_for("redis", check_redis, attempts, sleep_seconds)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise
