from datetime import UTC, datetime
from types import SimpleNamespace

from app.services.storage_service import StorageService


def test_resolve_job_dir_uses_normalized_name_when_db_job_has_no_storage_dir(monkeypatch, tmp_path) -> None:
    storage = StorageService(tmp_path, use_db_lookup=True)
    created_at = datetime(2026, 6, 17, 10, 41, 43, tzinfo=UTC)
    job = SimpleNamespace(
        id="1989e0a2-f826-4ef0-b11a-1bf3d4e183aa",
        platform="douyin",
        created_at=created_at,
        storage_dir=None,
    )
    persisted: list[tuple[str, str]] = []

    monkeypatch.setattr(storage, "_lookup_job_record", lambda job_id: job)
    monkeypatch.setattr(storage, "_find_existing_job_dir", lambda job_id: None)
    monkeypatch.setattr(storage, "_persist_storage_dir", lambda job_id, path: persisted.append((job_id, path)))

    path = storage.job_dir(job.id)

    assert path == tmp_path / "jobs" / "20260617-104143_job_1989e0a2"
    assert path.exists()
    assert persisted == [(job.id, "jobs/20260617-104143_job_1989e0a2")]


def test_resolve_job_dir_reuses_existing_legacy_folder_when_db_job_has_no_storage_dir(monkeypatch, tmp_path) -> None:
    storage = StorageService(tmp_path, use_db_lookup=True)
    created_at = datetime(2026, 6, 17, 7, 17, 23, tzinfo=UTC)
    job = SimpleNamespace(
        id="fe175e8a-b512-4e1d-a4d3-49f7edd636a0",
        platform="douyin",
        created_at=created_at,
        storage_dir=None,
    )
    legacy_path = tmp_path / "jobs" / "20260617-071723_douyin_fe175e8a"
    legacy_path.mkdir(parents=True)
    persisted: list[tuple[str, str]] = []

    monkeypatch.setattr(storage, "_lookup_job_record", lambda job_id: job)
    monkeypatch.setattr(storage, "_find_existing_job_dir", lambda job_id: legacy_path)
    monkeypatch.setattr(storage, "_persist_storage_dir", lambda job_id, path: persisted.append((job_id, path)))

    path = storage.job_dir(job.id)

    assert path == legacy_path
    assert persisted == [(job.id, "jobs/20260617-071723_douyin_fe175e8a")]


def test_to_storage_key_and_resolve_path_round_trip(tmp_path) -> None:
    storage = StorageService(tmp_path, use_db_lookup=False)
    absolute_path = tmp_path / "jobs" / "20260617-104143_job_1989e0a2" / "output_vi.mp4"

    storage_key = storage.to_storage_key(absolute_path)

    assert storage_key == "jobs/20260617-104143_job_1989e0a2/output_vi.mp4"
    assert storage.resolve_path(storage_key) == absolute_path


class FakeObjectClient:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_object(self, bucket: str, object_name: str, data, length: int, content_type: str) -> None:
        assert bucket == "douyin-prod"
        payload = data.read()
        assert length == len(payload)
        self.objects[object_name] = payload

    def fget_object(self, bucket: str, object_name: str, file_path: str) -> None:
        assert bucket == "douyin-prod"
        from pathlib import Path

        Path(file_path).write_bytes(self.objects[object_name])

    def presigned_get_object(self, bucket: str, object_name: str, expires) -> str:
        assert bucket == "douyin-prod"
        return f"https://cdn.example.com/{object_name}"


def test_object_storage_upload_and_materialize_round_trip(monkeypatch, tmp_path) -> None:
    client = FakeObjectClient()
    from app.services import storage_service as storage_module

    original_backend = storage_module.settings.storage_backend
    original_bucket = storage_module.settings.storage_bucket
    original_prefix = storage_module.settings.storage_prefix
    original_public_url_base = storage_module.settings.storage_public_url_base
    object.__setattr__(storage_module.settings, "storage_backend", "s3")
    object.__setattr__(storage_module.settings, "storage_bucket", "douyin-prod")
    object.__setattr__(storage_module.settings, "storage_prefix", "media")
    object.__setattr__(storage_module.settings, "storage_public_url_base", "https://cdn.example.com")

    try:
        storage = StorageService(tmp_path, use_db_lookup=False)
        monkeypatch.setattr(storage, "_build_object_client", lambda: client)

        stored_path = storage.write_text("job-1", "subtitles_vi.srt", "subtitle data")
        assert stored_path == "jobs/job-1/subtitles_vi.srt"
        assert client.objects["media/jobs/job-1/subtitles_vi.srt"] == b"subtitle data"

        local_path = storage.resolve_path(stored_path)
        local_path.unlink()
        restored = storage.resolve_path(stored_path)
        assert restored.read_text(encoding="utf-8") == "subtitle data"
        assert storage.get_download_url(stored_path) == "https://cdn.example.com/media/jobs/job-1/subtitles_vi.srt"
    finally:
        object.__setattr__(storage_module.settings, "storage_backend", original_backend)
        object.__setattr__(storage_module.settings, "storage_bucket", original_bucket)
        object.__setattr__(storage_module.settings, "storage_prefix", original_prefix)
        object.__setattr__(storage_module.settings, "storage_public_url_base", original_public_url_base)


def test_edit_dir_reuses_existing_folder_for_same_edit_id(tmp_path) -> None:
    first_storage = StorageService(tmp_path, use_db_lookup=False)
    job_id = "750e2ac0-f4bd-4360-8198-e9f5bbee31f4"
    created_at = datetime(2026, 6, 18, 13, 48, 40, tzinfo=UTC)

    first_storage.create_job_dir(job_id, "douyin", created_at)
    first_path = first_storage.edit_dir(job_id, "939a8fc0-6f8a-4cf4-9ef9-41f0d5b5fdaa")
    first_path.mkdir(parents=True, exist_ok=True)

    second_storage = StorageService(tmp_path, use_db_lookup=False)
    second_storage._job_dirs[job_id] = tmp_path / "jobs" / "20260618-134840_job_750e2ac0"
    second_path = second_storage.edit_dir(job_id, "939a8fc0-6f8a-4cf4-9ef9-41f0d5b5fdaa")

    assert second_path == first_path
