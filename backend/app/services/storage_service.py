import json
from io import BytesIO
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Job


class StorageService:
    OBJECT_BACKENDS = {"s3", "minio", "r2"}

    def __init__(self, storage_root: Path | None = None, use_db_lookup: bool | None = None) -> None:
        self.storage_root = storage_root or settings.storage_root
        self.storage_backend = settings.storage_backend
        self.storage_prefix = settings.storage_prefix
        self.storage_bucket = settings.storage_bucket
        self.use_db_lookup = use_db_lookup if use_db_lookup is not None else self.storage_root == settings.storage_root
        self._job_dirs: dict[str, Path] = {}
        self._edit_dirs: dict[tuple[str, str], Path] = {}
        self._object_client: Any | None = None

    def job_dir(self, job_id: str) -> Path:
        path = self._resolve_job_dir(job_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def build_job_dir_name(self, job_id: str, platform: str | None, created_at: Any) -> str:
        timestamp = created_at.strftime("%Y%m%d-%H%M%S")
        return f"{timestamp}_job_{job_id[:8]}"

    def create_job_dir(self, job_id: str, platform: str | None, created_at: Any) -> str:
        path = self.storage_root / "jobs" / self.build_job_dir_name(job_id, platform, created_at)
        path.mkdir(parents=True, exist_ok=True)
        self._job_dirs[job_id] = path
        return self.to_storage_key(path)

    def write_json(self, job_id: str, filename: str, data: Any) -> str:
        path = self._write_json_to_dir(self.job_dir(job_id), filename, data)
        return self.sync_file(path) or path

    def write_text(self, job_id: str, filename: str, content: str) -> str:
        path = self._write_text_to_dir(self.job_dir(job_id), filename, content)
        return self.sync_file(path) or path

    def edit_dir(self, job_id: str, edit_id: str) -> Path:
        key = (job_id, edit_id)
        if key not in self._edit_dirs:
            job_folder_name = self.job_dir(job_id).name
            existing_path = self._find_existing_edit_dir(job_folder_name, edit_id)
            self._edit_dirs[key] = existing_path or (
                self.storage_root / "edits" / job_folder_name / self.build_edit_dir_name(edit_id)
            )
        path = self._edit_dirs[key]
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def build_edit_dir_name(edit_id: str, created_at: datetime | None = None) -> str:
        timestamp = (created_at or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S")
        return f"{timestamp}_edit_{edit_id[:8]}"

    def write_edit_json(self, job_id: str, edit_id: str, filename: str, data: Any) -> str:
        path = self._write_json_to_dir(self.edit_dir(job_id, edit_id), filename, data)
        return self.sync_file(path) or path

    def write_edit_text(self, job_id: str, edit_id: str, filename: str, content: str) -> str:
        path = self._write_text_to_dir(self.edit_dir(job_id, edit_id), filename, content)
        return self.sync_file(path) or path

    def write_json_to_directory(self, directory: str | Path, filename: str, data: Any) -> str:
        path = self._write_json_to_dir(self.resolve_directory(directory), filename, data)
        return self.sync_file(path) or path

    def write_text_to_directory(self, directory: str | Path, filename: str, content: str) -> str:
        path = self._write_text_to_dir(self.resolve_directory(directory), filename, content)
        return self.sync_file(path) or path

    def read_json(self, job_id: str, filename: str) -> Any:
        path = self.job_dir(job_id) / filename
        return json.loads(path.read_text(encoding="utf-8"))

    def to_storage_key(self, value: str | Path) -> str:
        raw = str(value)
        if "://" in raw:
            return raw
        normalized = Path(raw)
        if normalized.is_absolute():
            try:
                normalized = normalized.relative_to(self.storage_root)
            except ValueError:
                return str(normalized)
        return normalized.as_posix()

    def resolve_path(self, value: str | Path) -> Path:
        raw = str(value)
        if "://" in raw:
            raise ValueError(f"Remote storage URLs are not valid local file paths: {raw}")
        normalized = Path(raw)
        if normalized.is_absolute():
            return normalized
        path = self.storage_root / normalized
        if self.uses_object_storage() and not path.exists():
            self._download_object_to_path(normalized.as_posix(), path)
        return path

    def resolve_directory(self, directory: str | Path) -> Path:
        raw = str(directory)
        if "://" in raw:
            raise ValueError(f"Remote storage URLs are not valid local directories: {raw}")
        normalized = Path(raw)
        if normalized.is_absolute():
            return normalized
        return self.storage_root / normalized

    def uses_object_storage(self) -> bool:
        return self.storage_backend in self.OBJECT_BACKENDS

    def sync_file(self, value: str | Path | None) -> str | None:
        if value is None:
            return None
        storage_key = self.to_storage_key(value)
        if not self.uses_object_storage() or "://" in storage_key:
            return storage_key
        local_path = self.resolve_path(storage_key)
        if local_path.exists() and local_path.is_file():
            self._upload_file(storage_key, local_path)
        return storage_key

    def get_download_url(self, value: str | Path) -> str:
        storage_key = self.to_storage_key(value)
        if "://" in storage_key:
            return storage_key
        if not self.uses_object_storage():
            raise ValueError("Local storage does not expose direct object download URLs.")
        return self._build_object_download_url(storage_key)

    @staticmethod
    def _write_json_to_dir(directory: Path, filename: str, data: Any) -> str:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / filename
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)

    @staticmethod
    def _write_text_to_dir(directory: Path, filename: str, content: str) -> str:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / filename
        path.write_text(content, encoding="utf-8")
        return str(path)

    def _resolve_job_dir(self, job_id: str) -> Path:
        if job_id in self._job_dirs:
            return self._job_dirs[job_id]

        if self.use_db_lookup:
            job = self._lookup_job_record(job_id)
            if job is not None:
                if job.storage_dir:
                    path = self.resolve_directory(job.storage_dir)
                    self._job_dirs[job_id] = path
                    return path

                existing_path = self._find_existing_job_dir(job_id)
                resolved_path = existing_path or self.storage_root / "jobs" / self.build_job_dir_name(
                    job.id,
                    job.platform,
                    job.created_at,
                )
                self._persist_storage_dir(job.id, self.to_storage_key(resolved_path))
                self._job_dirs[job_id] = resolved_path
                return resolved_path

        legacy_path = self._find_existing_job_dir(job_id)
        if legacy_path is not None:
            self._job_dirs[job_id] = legacy_path
            return legacy_path

        path = self.storage_root / "jobs" / job_id
        self._job_dirs[job_id] = path
        return path

    def _find_existing_job_dir(self, job_id: str) -> Path | None:
        exact_match = self.storage_root / "jobs" / job_id
        if exact_match.exists():
            return exact_match

        jobs_root = self.storage_root / "jobs"
        if not jobs_root.exists():
            return None

        short_id = job_id[:8]
        candidates = sorted(
            jobs_root.glob(f"*_{short_id}"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return candidates[0]
        return None

    def _find_existing_edit_dir(self, job_folder_name: str, edit_id: str) -> Path | None:
        edits_root = self.storage_root / "edits" / job_folder_name
        if not edits_root.exists():
            return None

        short_id = edit_id[:8]
        candidates = sorted(
            edits_root.glob(f"*_edit_{short_id}"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return candidates[0]
        return None

    def _upload_file(self, storage_key: str, local_path: Path) -> None:
        client = self._get_object_client()
        object_name = self._object_name(storage_key)
        content_type = self._guess_content_type(local_path)
        with local_path.open("rb") as handle:
            data = handle.read()
        client.put_object(
            self._require_bucket(),
            object_name,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def _download_object_to_path(self, storage_key: str, target_path: Path) -> None:
        client = self._get_object_client()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        client.fget_object(self._require_bucket(), self._object_name(storage_key), str(target_path))

    def _build_object_download_url(self, storage_key: str) -> str:
        object_name = self._object_name(storage_key)
        public_base = settings.storage_public_url_base
        if public_base:
            return f"{public_base.rstrip('/')}/{object_name}"
        client = self._get_object_client()
        expires = timedelta(seconds=max(60, settings.storage_presign_expiry_seconds))
        return client.presigned_get_object(self._require_bucket(), object_name, expires=expires)

    def _object_name(self, storage_key: str) -> str:
        key = storage_key.strip("/")
        if not self.storage_prefix:
            return key
        return f"{self.storage_prefix}/{key}"

    def _require_bucket(self) -> str:
        if not self.storage_bucket:
            raise ValueError("STORAGE_BUCKET is required when using object storage backends.")
        return self.storage_bucket

    def _get_object_client(self) -> Any:
        if not self.uses_object_storage():
            raise ValueError(f"Storage backend does not use object storage: {self.storage_backend}")
        if self._object_client is None:
            self._object_client = self._build_object_client()
        return self._object_client

    def _build_object_client(self) -> Any:
        if not settings.storage_endpoint_url:
            raise ValueError("STORAGE_ENDPOINT_URL is required when using object storage backends.")
        try:
            from minio import Minio
        except ImportError as exc:
            raise RuntimeError("Install the `minio` package to use object storage backends.") from exc

        endpoint = settings.storage_endpoint_url.replace("https://", "").replace("http://", "").rstrip("/")
        return Minio(
            endpoint,
            access_key=settings.storage_access_key,
            secret_key=settings.storage_secret_key,
            secure=settings.storage_secure,
            region=settings.storage_region or None,
        )

    @staticmethod
    def _guess_content_type(path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".json":
            return "application/json"
        if suffix == ".srt":
            return "application/x-subrip"
        if suffix == ".mp4":
            return "video/mp4"
        if suffix == ".wav":
            return "audio/wav"
        if suffix == ".mp3":
            return "audio/mpeg"
        return "application/octet-stream"

    @staticmethod
    def _lookup_job_record(job_id: str) -> Any | None:
        db = SessionLocal()
        try:
            job = db.get(Job, job_id)
            if job is None:
                return None
            return SimpleNamespace(
                id=job.id,
                platform=job.platform,
                created_at=job.created_at,
                storage_dir=job.storage_dir,
            )
        finally:
            db.close()

    @staticmethod
    def _persist_storage_dir(job_id: str, storage_dir: str) -> None:
        db = SessionLocal()
        try:
            job = db.get(Job, job_id)
            if job is None or job.storage_dir == storage_dir:
                return
            job.storage_dir = storage_dir
            db.commit()
        finally:
            db.close()
