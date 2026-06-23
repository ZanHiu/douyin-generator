from celery import Celery
from celery.signals import worker_ready

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.job_service import JobService

celery_app = Celery(
    "douyin_generator",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


def collect_active_task_ids() -> set[str]:
    try:
        inspect = celery_app.control.inspect(timeout=1.0)
        active = inspect.active() or {}
        reserved = inspect.reserved() or {}
        scheduled = inspect.scheduled() or {}
    except Exception:
        return set()

    task_ids: set[str] = set()
    for payload in [active, reserved]:
        for items in payload.values():
            for item in items or []:
                task_id = item.get("id")
                if task_id:
                    task_ids.add(str(task_id))

    for items in scheduled.values():
        for item in items or []:
            request = item.get("request") or {}
            task_id = request.get("id")
            if task_id:
                task_ids.add(str(task_id))

    return task_ids


def recover_queue_state() -> list[str]:
    db = SessionLocal()
    try:
        return JobService(db).recover_incomplete_jobs(active_task_ids=collect_active_task_ids())
    finally:
        db.close()


@worker_ready.connect
def on_worker_ready(**_kwargs) -> None:
    recover_queue_state()
