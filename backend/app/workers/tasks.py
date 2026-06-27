from app.db.session import SessionLocal
from app.services.errors import ProcessingError
from app.services.edit_render_service import fail_edit_render, run_edit_render
from app.services.job_service import JobService
from app.services.mock_pipeline import MockPipeline
from app.workers.celery_app import celery_app, recover_queue_state


@celery_app.task(name="process_job")
def process_job(job_id: str) -> None:
    db = SessionLocal()
    jobs = JobService(db)
    try:
        recover_queue_state()
        job = jobs.get_job(job_id)
        if job is None:
            raise ProcessingError("UNKNOWN_ERROR", f"Job not found: {job_id}")
        if job.status in {"cancelled", "cancelling"} or job.cancel_requested:
            jobs.mark_cancelled(job_id, "cancelled", "Job cancelled")
            return
        MockPipeline(jobs).run(job_id)
    except ProcessingError as exc:
        if exc.message == "Job cancelled":
            jobs.mark_cancelled(job_id, "cancelled", "Job cancelled")
            return
        jobs.mark_failed(job_id, "processing", exc.message)
        raise
    except Exception as exc:
        jobs.mark_failed(job_id, "mock_pipeline", str(exc))
        raise
    finally:
        db.close()


@celery_app.task(name="render_job_edit")
def render_job_edit(job_id: str, edit_id: str) -> None:
    db = SessionLocal()
    jobs = JobService(db)
    try:
        recover_queue_state()
        run_edit_render(jobs, job_id=job_id, edit_id=edit_id, task_id=render_job_edit.request.id)
    except ProcessingError as exc:
        fail_edit_render(jobs, job_id=job_id, edit_id=edit_id, error_message=exc.message)
        raise
    except Exception as exc:
        fail_edit_render(jobs, job_id=job_id, edit_id=edit_id, error_message=str(exc))
        raise
    finally:
        db.close()
