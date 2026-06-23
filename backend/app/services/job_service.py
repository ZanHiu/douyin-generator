from datetime import UTC, datetime, timedelta

from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Query, Session

from app.core.config import settings
from app.models import Job, JobEdit, JobLog
from app.schemas.job import JobCreate, JobEditSort, JobEditToolFilter, JobSort, JobStatus
from app.services.storage_service import StorageService
from app.services.user_settings_service import UserSettingsService
from app.services.video_resolver_service import VideoResolverService


class JobService:
    STORAGE_PATH_FIELDS = {
        "storage_dir",
        "input_video_path",
        "audio_path",
        "transcript_zh_path",
        "transcript_vi_path",
        "subtitle_path",
        "tts_audio_path",
        "output_video_path",
    }

    def __init__(self, db: Session, storage: StorageService | None = None) -> None:
        self.db = db
        self.storage = storage or StorageService()

    def create_job(self, payload: JobCreate, *, initial_render_config: dict | None = None) -> Job:
        job = Job(
            source_url=payload.source_url,
            platform=self._detect_platform(payload.source_url),
            status="queued",
            stage="created",
            progress=0,
            retry_count=0,
            voice_id=payload.voice_id,
            burn_subtitle=payload.burn_subtitle,
            mix_original_audio=payload.mix_original_audio,
            cancel_requested=False,
            queued_at=datetime.now(UTC),
            final_config_json=initial_render_config,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        job.storage_dir = self.storage.create_job_dir(job.id, job.platform, job.created_at)
        self.db.commit()
        self.db.refresh(job)
        self._write_manifest(job)
        self.log(job.id, "info", "created", "Job created")
        return job

    def get_job(self, job_id: str) -> Job | None:
        return (
            self.db.query(Job)
            .filter(Job.id == job_id)
            .populate_existing()
            .one_or_none()
        )

    def list_jobs(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: JobStatus | None = None,
        sort: JobSort = "newest",
    ) -> tuple[list[Job], int]:
        bounded_page = max(1, page)
        bounded_page_size = max(1, min(page_size, 100))
        query = self._jobs_query(search=search, status=status)
        total = query.count()
        query = self._apply_jobs_sort(query, sort)
        jobs = (
            query.offset((bounded_page - 1) * bounded_page_size)
            .limit(bounded_page_size)
            .all()
        )
        return list(jobs), total

    def list_logs(self, job_id: str) -> list[JobLog]:
        self._require_job(job_id)
        return list(
            self.db.query(JobLog)
            .filter(JobLog.job_id == job_id)
            .order_by(JobLog.created_at.asc())
            .all()
        )

    def create_edit(
        self,
        job_id: str,
        *,
        edit_id: str,
        tool_summary: str,
        config_json: dict,
        output_video_path: str | None,
        result_url: str | None,
        is_draft: bool = False,
    ) -> JobEdit:
        self._require_job(job_id)
        version_number = None if is_draft else self._next_edit_version(job_id)
        edit = JobEdit(
            id=edit_id,
            job_id=job_id,
            version_number=version_number,
            tool_summary=tool_summary,
            is_draft=is_draft,
            config_json=config_json,
            output_video_path=self.storage.sync_file(
                self._normalize_storage_value("output_video_path", output_video_path)
            ),
            result_url=result_url,
        )
        self.db.add(edit)
        self.db.commit()
        self.db.refresh(edit)
        if not is_draft:
            self._write_edit_manifest(edit)
        return edit

    def update_edit(
        self,
        edit_id: str,
        *,
        tool_summary: str,
        config_json: dict,
        output_video_path: str | None,
        result_url: str | None,
    ) -> JobEdit:
        edit = self.get_edit(edit_id)
        if edit is None:
            raise ValueError(f"Edit not found: {edit_id}")
        edit.tool_summary = tool_summary
        edit.config_json = config_json
        edit.output_video_path = self.storage.sync_file(
            self._normalize_storage_value("output_video_path", output_video_path)
        )
        edit.result_url = result_url
        self.db.commit()
        self.db.refresh(edit)
        self._write_edit_manifest(edit)
        return edit

    def list_edits(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        tool: JobEditToolFilter = "all",
        sort: JobEditSort = "newest",
    ) -> tuple[list[JobEdit], int]:
        bounded_page = max(1, page)
        bounded_page_size = max(1, min(page_size, 100))
        query = self._edits_query(search=search, tool=tool).filter(JobEdit.is_draft.is_(False))
        query = self._apply_edits_sort(query, sort)
        total = query.count()
        edits = (
            query.offset((bounded_page - 1) * bounded_page_size)
            .limit(bounded_page_size)
            .all()
        )
        return list(edits), total

    def get_edit(self, edit_id: str) -> JobEdit | None:
        return self.db.get(JobEdit, edit_id)

    def _next_edit_version(self, job_id: str) -> int:
        current_max = (
            self.db.query(func.max(JobEdit.version_number))
            .filter(JobEdit.job_id == job_id, JobEdit.is_draft.is_(False))
            .scalar()
        )
        return int(current_max or 0) + 1

    def mark_processing(self, job_id: str, stage: str, progress: int, message: str) -> Job:
        job = self._require_job(job_id)
        if job.status in {"cancelled", "cancelling"} or job.cancel_requested:
            return job
        job.status = "processing"
        job.stage = stage
        job.progress = progress
        if job.started_at is None:
            job.started_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        self.db.commit()
        self.log(job_id, "info", stage, message)
        self.db.refresh(job)
        return job

    def attach_artifact(self, job_id: str, field_name: str, path: str) -> None:
        job = self._require_job(job_id)
        if job.status in {"cancelled", "cancelling"}:
            return
        normalized_value = self._normalize_storage_value(field_name, path)
        if field_name in self.STORAGE_PATH_FIELDS:
            normalized_value = self.storage.sync_file(normalized_value)
        setattr(job, field_name, normalized_value)
        self.db.commit()

    def set_task_id(self, job_id: str, task_id: str | None) -> Job:
        job = self._require_job(job_id)
        job.task_id = task_id
        if job.status == "queued" and job.queued_at is None:
            job.queued_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(job)
        return job

    def mark_completed(self, job_id: str) -> Job:
        job = self._require_job(job_id)
        if job.status in {"cancelled", "cancelling"}:
            return job
        job.status = "completed"
        job.stage = "completed"
        job.progress = 100
        job.result_url = f"/api/jobs/{job_id}/download"
        job.subtitle_url = f"/api/jobs/{job_id}/subtitles"
        job.completed_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        job.cancel_requested = False
        job.cancel_requested_at = None
        job.task_id = None
        self.db.commit()
        self.db.refresh(job)
        self._write_manifest(job)
        self.log(job_id, "info", "completed", "Job completed")
        return job

    def mark_failed(self, job_id: str, stage: str, error_message: str) -> Job:
        job = self._require_job(job_id)
        if job.status == "cancelled":
            return job
        job.status = "failed"
        job.stage = "failed"
        job.error_message = error_message
        job.updated_at = datetime.now(UTC)
        job.cancel_requested = False
        job.cancel_requested_at = None
        job.task_id = None
        self.db.commit()
        self.db.refresh(job)
        self._write_manifest(job)
        self.log(job_id, "error", stage, error_message)
        return job

    def mark_cancelled(self, job_id: str, stage: str = "cancelled", message: str = "Job cancelled") -> Job:
        job = self._require_job(job_id)
        job.status = "cancelled"
        job.stage = stage
        job.error_message = None
        job.cancel_requested = False
        job.cancel_requested_at = None
        job.task_id = None
        job.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(job)
        self._write_manifest(job)
        self.log(job_id, "info", stage, message)
        return job

    def request_cancel(self, job_id: str) -> Job:
        job = self._require_job(job_id)
        if job.status not in {"queued", "processing"}:
            raise ValueError("Only queued or processing jobs can be cancelled.")
        if job.status == "queued":
            return self.mark_cancelled(job_id, "cancelled", "Job cancelled")
        job.status = "cancelling"
        job.cancel_requested = True
        job.cancel_requested_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(job)
        self._write_manifest(job)
        self.log(job_id, "info", "cancelling", "Cancellation requested")
        self.log(job_id, "info", "cancelling", "Waiting for the current stage to stop safely")
        return job

    def retry_job(self, job_id: str) -> Job:
        job = self._require_job(job_id)
        if job.status not in {"failed", "cancelled"}:
            raise ValueError("Only failed or cancelled jobs can be retried.")
        job.status = "queued"
        job.stage = "created"
        job.progress = 0
        job.retry_count = int(job.retry_count or 0) + 1
        job.error_message = None
        job.result_url = None
        job.subtitle_url = None
        job.completed_at = None
        job.cancel_requested = False
        job.cancel_requested_at = None
        job.queued_at = datetime.now(UTC)
        job.started_at = None
        job.task_id = None
        job.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(job)
        self._write_manifest(job)
        self.log(job_id, "info", "created", "Job re-queued")
        return job

    def is_cancel_requested(self, job_id: str) -> bool:
        job = self._require_job(job_id)
        return bool(job.cancel_requested) or job.status in {"cancelling", "cancelled"}

    def is_cancelled(self, job_id: str) -> bool:
        job = self._require_job(job_id)
        return job.status == "cancelled"

    def log(
        self,
        job_id: str,
        level: str,
        stage: str | None,
        message: str,
        data: dict | None = None,
    ) -> None:
        self.db.add(JobLog(job_id=job_id, level=level, stage=stage, message=message, data=data))
        self.db.commit()

    def recover_incomplete_jobs(self, active_task_ids: set[str] | None = None) -> list[str]:
        active_task_ids = active_task_ids or set()
        recovered: list[str] = []
        now = datetime.now(UTC)
        stale_cutoff = now - timedelta(minutes=settings.queue_stale_job_minutes)
        cancelling_cutoff = now - timedelta(seconds=settings.queue_cancellation_grace_seconds)

        jobs = self.db.query(Job).filter(Job.status.in_(["queued", "processing", "cancelling"])).all()
        for job in jobs:
            if job.status == "cancelling" and job.cancel_requested_at and job.cancel_requested_at <= cancelling_cutoff:
                self.mark_cancelled(job.id, "cancelled", "Recovered stale cancellation")
                recovered.append(job.id)
                continue

            if not job.task_id:
                if job.status == "processing" and job.updated_at and job.updated_at <= stale_cutoff:
                    self.mark_failed(job.id, "recovery", "Recovered orphaned processing job.")
                    recovered.append(job.id)
                continue

            if job.task_id in active_task_ids:
                continue

            if job.status == "queued":
                job.task_id = None
                job.updated_at = now
                self.db.commit()
                self._write_manifest(job)
                self.log(job.id, "info", "recovery", "Cleared orphaned queued task reference")
                recovered.append(job.id)
                continue

            if job.status == "processing" and job.updated_at and job.updated_at <= stale_cutoff:
                self.mark_failed(job.id, "recovery", "Recovered orphaned processing job.")
                recovered.append(job.id)
                continue

            if job.status == "cancelling" and job.updated_at and job.updated_at <= cancelling_cutoff:
                self.mark_cancelled(job.id, "cancelled", "Recovered stale cancellation")
                recovered.append(job.id)

        return recovered

    @staticmethod
    def build_editor_baseline_config(job: Job) -> dict:
        return UserSettingsService.build_job_render_defaults(
            burn_subtitle=bool(job.burn_subtitle),
            mix_original_audio=bool(job.mix_original_audio),
            settings_payload=UserSettingsService.default_settings(),
        )

    def _require_job(self, job_id: str) -> Job:
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")
        return job

    @staticmethod
    def _detect_platform(source_url: str) -> str | None:
        return VideoResolverService.detect_platform(source_url)

    def _normalize_storage_value(self, field_name: str, value: str | None) -> str | None:
        if value is None or field_name not in self.STORAGE_PATH_FIELDS:
            return value
        return self.storage.to_storage_key(value)

    def _write_manifest(self, job: Job) -> None:
        if not job.storage_dir:
            return
        self.storage.write_json_to_directory(
            job.storage_dir,
            "job_manifest.json",
            {
                "job_id": job.id,
                "storage_backend": settings.storage_backend,
                "storage_dir": job.storage_dir,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "source_url": job.source_url,
                "platform": job.platform,
                "status": job.status,
                "stage": job.stage,
                "progress": job.progress,
                "retry_count": job.retry_count,
                "error_message": job.error_message,
                "cancel_requested": job.cancel_requested,
                "queued_at": job.queued_at.isoformat() if job.queued_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "cancel_requested_at": job.cancel_requested_at.isoformat() if job.cancel_requested_at else None,
                "task_id": job.task_id,
                "voice_id": job.voice_id,
                "burn_subtitle": job.burn_subtitle,
                "mix_original_audio": job.mix_original_audio,
            },
        )

    def _write_edit_manifest(self, edit: JobEdit) -> None:
        directory = self.storage.edit_dir(edit.job_id, edit.id)
        self.storage.write_json_to_directory(
            directory,
            "edit_manifest.json",
            {
                "edit_id": edit.id,
                "job_id": edit.job_id,
                "version_number": edit.version_number,
                "tool_summary": edit.tool_summary,
                "is_draft": edit.is_draft,
                "result_url": edit.result_url,
                "output_video_path": edit.output_video_path,
                "created_at": edit.created_at.isoformat() if edit.created_at else None,
                "updated_at": edit.updated_at.isoformat() if edit.updated_at else None,
                "config_json": edit.config_json,
            },
        )

    def _jobs_query(self, search: str | None, status: JobStatus | None) -> Query:
        query = self.db.query(Job)

        if status:
            query = query.filter(Job.status == status)

        normalized_search = (search or "").strip()
        if normalized_search:
            pattern = f"%{normalized_search}%"
            query = query.filter(
                or_(
                    Job.id.ilike(pattern),
                    Job.source_url.ilike(pattern),
                    Job.platform.ilike(pattern),
                    Job.stage.ilike(pattern),
                    Job.status.ilike(pattern),
                )
            )

        return query

    @staticmethod
    def _apply_jobs_sort(query: Query, sort: JobSort) -> Query:
        if sort == "oldest":
            return query.order_by(asc(Job.created_at), asc(Job.id))
        if sort == "progress":
            return query.order_by(desc(Job.progress), desc(Job.created_at), desc(Job.id))
        return query.order_by(desc(Job.created_at), desc(Job.id))

    @staticmethod
    def _apply_edits_sort(query: Query, sort: JobEditSort) -> Query:
        if sort == "oldest":
            return query.order_by(asc(JobEdit.updated_at), asc(JobEdit.created_at), asc(JobEdit.id))
        return query.order_by(desc(JobEdit.updated_at), desc(JobEdit.created_at), desc(JobEdit.id))

    def _edits_query(self, search: str | None, tool: JobEditToolFilter) -> Query:
        query = self.db.query(JobEdit)

        if tool != "all":
            query = query.filter(JobEdit.tool_summary.ilike(f"%{tool.capitalize()}%"))

        normalized_search = (search or "").strip()
        if normalized_search:
            pattern = f"%{normalized_search}%"
            query = query.filter(
                or_(
                    JobEdit.id.ilike(pattern),
                    JobEdit.job_id.ilike(pattern),
                    JobEdit.tool_summary.ilike(pattern),
                )
            )

        return query
