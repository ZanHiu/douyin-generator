from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import require_authenticated_user
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User
from app.schemas.job import JobCreate
from app.services.job_service import JobService
from app.services.storage_service import StorageService
from app.services.video_renderer_service import VideoRendererService


@pytest.fixture()
def db_session(tmp_path) -> Generator[Session, None, None]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session, tmp_path) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def override_require_authenticated_user() -> User:
        return User(
            id="test-user-001",
            email="tester@example.com",
            password_hash="not-used",
            is_active=True,
            is_admin=True,
            settings_json={},
        )

    original_storage_root = settings.storage_root
    original_storage_backend = settings.storage_backend
    original_storage_bucket = settings.storage_bucket
    original_storage_prefix = settings.storage_prefix
    original_storage_public_url_base = settings.storage_public_url_base
    object.__setattr__(settings, "storage_root", tmp_path)
    object.__setattr__(settings, "storage_backend", "local")
    object.__setattr__(settings, "storage_bucket", None)
    object.__setattr__(settings, "storage_prefix", "")
    object.__setattr__(settings, "storage_public_url_base", None)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_authenticated_user] = override_require_authenticated_user
    try:
        yield TestClient(app)
    finally:
        object.__setattr__(settings, "storage_root", original_storage_root)
        object.__setattr__(settings, "storage_backend", original_storage_backend)
        object.__setattr__(settings, "storage_bucket", original_storage_bucket)
        object.__setattr__(settings, "storage_prefix", original_storage_prefix)
        object.__setattr__(settings, "storage_public_url_base", original_storage_public_url_base)
        app.dependency_overrides.clear()


def test_list_jobs_returns_recent_jobs(client: TestClient, db_session: Session, tmp_path) -> None:
    service = JobService(db_session, StorageService(tmp_path, use_db_lookup=False))
    first = service.create_job(
        JobCreate(source_url="https://www.douyin.com/video/111", voice_id="vi_female_01")
    )
    second = service.create_job(
        JobCreate(source_url="https://www.tiktok.com/@demo/video/222", voice_id="vi_female_01")
    )

    response = client.get("/api/jobs?page=1&page_size=10")

    assert response.status_code == 200
    data = response.json()
    job_ids = {item["job_id"] for item in data["items"]}
    assert job_ids == {first.id, second.id}
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total_pages"] == 1
    assert data["items"][0]["created_at"] >= data["items"][1]["created_at"]


def test_create_uploaded_job_persists_input_video_and_enqueues(
    client: TestClient,
    db_session: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeTask:
        id = "upload-task-001"

    def fake_delay(job_id: str) -> FakeTask:
        return FakeTask()

    monkeypatch.setattr("app.api.jobs.process_job.delay", fake_delay)

    response = client.post(
        "/api/jobs/upload",
        files={"source_file": ("demo.mp4", b"fake video bytes", "video/mp4")},
        data={
            "voice_id": "vi_female_01",
            "burn_subtitle": "true",
            "mix_original_audio": "false",
        },
    )

    assert response.status_code == 201
    job_id = response.json()["job_id"]
    service = JobService(db_session, StorageService(tmp_path, use_db_lookup=False))
    job = service.get_job(job_id)
    assert job is not None
    assert job.source_url == "upload://demo.mp4"
    assert job.input_video_path is not None
    input_path = storage_path = service.storage.resolve_path(job.input_video_path)
    assert input_path.exists()
    assert input_path.read_bytes() == b"fake video bytes"
    metadata_path = service.storage.job_dir(job_id) / "metadata.json"
    assert metadata_path.exists()


def test_list_jobs_supports_pagination_and_filters(
    client: TestClient,
    db_session: Session,
    tmp_path,
) -> None:
    service = JobService(db_session, StorageService(tmp_path, use_db_lookup=False))
    first = service.create_job(
        JobCreate(source_url="https://www.douyin.com/video/111", voice_id="vi_female_01")
    )
    second = service.create_job(
        JobCreate(source_url="https://www.tiktok.com/@demo/video/222", voice_id="vi_female_01")
    )
    service.mark_completed(second.id)
    service.mark_failed(first.id, "testing", "Test failure")

    response = client.get("/api/jobs?page=1&page_size=1&status=completed&search=tiktok&sort=oldest")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["total_pages"] == 1
    assert [item["job_id"] for item in data["items"]] == [second.id]


def test_get_job_editor_state_returns_transcript_segments(
    client: TestClient,
    db_session: Session,
    tmp_path,
) -> None:
    storage = StorageService(tmp_path, use_db_lookup=False)
    service = JobService(db_session, storage)
    job = service.create_job(
        JobCreate(source_url="https://www.douyin.com/video/111", voice_id="vi_female_01")
    )
    transcript_path = storage.write_json(
        job.id,
        "transcript_vi.json",
        [
            {"id": 0, "start": 0.0, "end": 1.2, "text_vi": "Xin chao", "text_zh": "ni hao"},
            {"id": 1, "start": 1.3, "end": 2.8, "text_vi": "Tam biet", "text_zh": "zai jian"},
        ],
    )
    service.attach_artifact(job.id, "transcript_vi_path", transcript_path)
    service.attach_artifact(
        job.id,
        "final_config_json",
        {
            "burn_subtitle": False,
            "original_volume_percent": 0,
            "subtitle_font_size": 18,
            "subtitle_position": "bottom",
        },
    )

    response = client.get(f"/api/jobs/{job.id}/editor-state")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job.id
    assert len(data["subtitle_segments"]) == 2
    assert data["subtitle_segments"][0]["text_vi"] == "Xin chao"
    assert data["render_config"]["burn_subtitle"] is False
    assert data["render_config"]["original_volume_percent"] == 0
    assert data["draft"] is None


def test_get_job_editor_state_returns_latest_draft_when_available(
    client: TestClient,
    db_session: Session,
    tmp_path,
) -> None:
    storage = StorageService(tmp_path, use_db_lookup=False)
    service = JobService(db_session, storage)
    job = service.create_job(
        JobCreate(source_url="https://www.douyin.com/video/111", voice_id="vi_female_01")
    )
    transcript_path = storage.write_json(
        job.id,
        "transcript_vi.json",
        [{"id": 0, "start": 0.0, "end": 1.2, "text_vi": "Xin chao", "text_zh": "ni hao"}],
    )
    service.attach_artifact(job.id, "transcript_vi_path", transcript_path)
    service.attach_artifact(job.id, "final_config_json", service.build_editor_baseline_config(job))
    draft = service.save_draft(
        job.id,
        config_json={"overlay_enabled": True, "overlay_text": "Draft"},
        tool_summary="Video :: Overlay",
    )

    response = client.get(f"/api/jobs/{job.id}/editor-state")

    assert response.status_code == 200
    data = response.json()
    assert data["draft"]["draft_id"] == draft.id
    assert data["draft"]["config"]["overlay_enabled"] is True


def test_save_job_editor_draft_persists_latest_config(
    client: TestClient,
    db_session: Session,
    tmp_path,
) -> None:
    storage = StorageService(tmp_path, use_db_lookup=False)
    service = JobService(db_session, storage)
    job = service.create_job(
        JobCreate(source_url="https://www.douyin.com/video/111", voice_id="vi_female_01")
    )
    service.mark_completed(job.id)

    response = client.put(
        f"/api/jobs/{job.id}/draft",
        json={
            "trim_start_seconds": 0.0,
            "trim_end_seconds": None,
            "playback_speed": 1.0,
            "blur_original_subtitles": True,
                "blur_x_ratio": 0.1,
                "blur_y_ratio": 0.7,
                "blur_width_ratio": 0.8,
                "blur_height_ratio": 0.2,
                "blur_strength": 11,
                "voice_volume_percent": 100,
                "original_volume_percent": 35,
                "burn_audio": True,
                "burn_original_audio": True,
                "burn_subtitle": True,
                "subtitle_font_size": 18,
                "subtitle_position": "bottom",
                "subtitle_text_color": "#FFFFFF",
            "subtitle_segments": None,
            "overlay_enabled": True,
            "overlay_text": "Draft overlay",
            "overlay_position": "custom",
            "overlay_x_ratio": 0.3,
            "overlay_y_ratio": 0.2,
            "overlay_font_size": 18,
            "overlay_text_color": "#FFFFFF",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["config"]["overlay_position"] == "custom"
    assert data["config"]["blur_width_ratio"] == 0.8

    draft = service.get_latest_draft(job.id)
    assert draft is not None
    assert draft.is_draft is True


def test_get_job_logs_returns_job_logs(client: TestClient, db_session: Session, tmp_path) -> None:
    service = JobService(db_session, StorageService(tmp_path, use_db_lookup=False))
    job = service.create_job(
        JobCreate(source_url="https://www.douyin.com/video/111", voice_id="vi_female_01")
    )
    service.log(job.id, "info", "testing", "Extra log")

    response = client.get(f"/api/jobs/{job.id}/logs")

    assert response.status_code == 200
    messages = [item["message"] for item in response.json()]
    assert messages == ["Job created", "Extra log"]


def test_get_job_logs_returns_404_for_missing_job(client: TestClient) -> None:
    response = client.get("/api/jobs/missing/logs")

    assert response.status_code == 404


def test_cancel_job_marks_queued_job_cancelled(
    client: TestClient,
    db_session: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = JobService(db_session, StorageService(tmp_path, use_db_lookup=False))
    job = service.create_job(
        JobCreate(source_url="https://www.douyin.com/video/111", voice_id="vi_female_01")
    )
    service.set_task_id(job.id, "task-queued-001")

    revoked: list[tuple[str, bool]] = []

    def fake_revoke(task_id: str, terminate: bool = False) -> None:
        revoked.append((task_id, terminate))

    monkeypatch.setattr("app.api.jobs.celery_app.control.revoke", fake_revoke)

    response = client.post(f"/api/jobs/{job.id}/cancel")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"
    assert revoked == [("task-queued-001", False)]
    refreshed = service.get_job(job.id)
    assert refreshed is not None
    assert refreshed.status == "cancelled"
    assert refreshed.task_id is None


def test_retry_job_requeues_failed_job(
    client: TestClient,
    db_session: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = JobService(db_session, StorageService(tmp_path, use_db_lookup=False))
    job = service.create_job(
        JobCreate(source_url="https://www.douyin.com/video/222", voice_id="vi_female_01")
    )
    service.mark_failed(job.id, "testing", "boom")

    class FakeTask:
        id = "retry-task-123"

    def fake_delay(job_id: str) -> FakeTask:
        assert job_id == job.id
        return FakeTask()

    monkeypatch.setattr("app.api.jobs.process_job.delay", fake_delay)

    response = client.post(f"/api/jobs/{job.id}/retry")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job.id
    assert data["status"] == "queued"
    refreshed = service.get_job(job.id)
    assert refreshed is not None
    assert refreshed.status == "queued"
    assert refreshed.progress == 0
    assert refreshed.task_id == "retry-task-123"
    assert refreshed.error_message is None


def test_render_edit_endpoint_returns_download_url_and_tool_details(
    client: TestClient,
    db_session: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = StorageService(tmp_path, use_db_lookup=False)
    service = JobService(db_session, storage)
    job = service.create_job(
        JobCreate(source_url="https://www.douyin.com/video/111", voice_id="vi_female_01")
    )
    service.attach_artifact(job.id, "input_video_path", storage.write_text(job.id, "input.mp4", "video"))
    service.attach_artifact(job.id, "audio_path", storage.write_text(job.id, "audio.wav", "audio"))
    service.attach_artifact(job.id, "subtitle_path", storage.write_text(job.id, "subtitles_vi.srt", "subtitle"))
    service.attach_artifact(job.id, "tts_audio_path", storage.write_text(job.id, "voice_vi.wav", "voice"))
    service.attach_artifact(
        job.id,
        "transcript_vi_path",
        storage.write_json(
            job.id,
            "transcript_vi.json",
            [
                {"id": 0, "start": 0.0, "end": 2.4, "text_vi": "Xin chao moi nguoi", "text_zh": "ni hao"},
                {"id": 1, "start": 2.5, "end": 5.0, "text_vi": "Cach lam nay rat don gian", "text_zh": "hen jiandan"},
            ],
        ),
    )
    service.mark_completed(job.id)

    def fake_render_edit(self, job_id: str, edit_id: str, *args, **kwargs) -> str:
        return storage.write_edit_text(job_id, edit_id, kwargs["output_filename"], "edited video")

    monkeypatch.setattr(VideoRendererService, "render_edit", fake_render_edit)

    response = client.post(
        f"/api/jobs/{job.id}/edits/render",
        json={
            "trim_start_seconds": 1.0,
            "trim_end_seconds": 10.0,
            "playback_speed": 1.1,
            "blur_original_subtitles": True,
                "blur_x_ratio": 0.0,
                "blur_y_ratio": 0.78,
                "blur_width_ratio": 1.0,
                "blur_height_ratio": 0.22,
                "blur_strength": 11,
                "voice_volume_percent": 100,
                "original_volume_percent": 35,
                "burn_audio": True,
                "burn_original_audio": True,
                "burn_subtitle": True,
                "subtitle_font_size": 24,
                "subtitle_position": "bottom",
                "subtitle_text_color": "#FFFFFF",
            "subtitle_segments": [
                {"id": 0, "start": 0.0, "end": 2.6, "text_vi": "Xin chao tat ca moi nguoi", "text_zh": "ni hao"},
                {"id": 1, "start": 2.8, "end": 5.0, "text_vi": "Cach lam nay rat don gian", "text_zh": "hen jiandan"},
            ],
            "overlay_enabled": True,
            "overlay_text": "Demo overlay",
            "overlay_position": "top_right",
            "overlay_x_ratio": 0.0,
            "overlay_y_ratio": 0.0,
            "overlay_font_size": 18,
            "overlay_text_color": "#FFFFFF",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job.id
    assert data["edit_id"]
    assert data["result_url"] == f"/api/jobs/{job.id}/edits/{data['edit_id']}/download"

    download_response = client.get(data["result_url"])
    assert download_response.status_code == 200

    edits_response = client.get("/api/jobs/edits?page=1&page_size=10")
    assert edits_response.status_code == 200
    edit_item = edits_response.json()["items"][0]
    assert edit_item["job_id"] == job.id
    assert edit_item["tool_group"] == "Video + Audio + Captions"
    assert (
        edit_item["tool_options"]
        == "Trim/Speed + Blur/Mask + Overlay + Burn original voice + Style/Position + Caption editor + Timing editor"
    )


def test_download_result_redirects_to_object_storage_when_remote_backend_enabled(
    client: TestClient,
    db_session: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    object.__setattr__(settings, "storage_backend", "s3")
    object.__setattr__(settings, "storage_bucket", "douyin-prod")
    object.__setattr__(settings, "storage_prefix", "media")
    object.__setattr__(settings, "storage_public_url_base", "https://cdn.example.com")

    class FakeObjectClient:
        def put_object(self, bucket: str, object_name: str, data: bytes, length: int, content_type: str) -> None:
            return None

        def fget_object(self, bucket: str, object_name: str, file_path: str) -> None:
            return None

        def presigned_get_object(self, bucket: str, object_name: str, expires) -> str:
            return f"https://cdn.example.com/{object_name}"

    monkeypatch.setattr(StorageService, "_build_object_client", lambda self: FakeObjectClient())

    storage = StorageService(tmp_path, use_db_lookup=False)
    service = JobService(db_session, storage)
    job = service.create_job(
        JobCreate(source_url="https://www.douyin.com/video/111", voice_id="vi_female_01")
    )
    output_path = storage.write_text(job.id, "output_vi.mp4", "video")
    service.attach_artifact(job.id, "output_video_path", output_path)
    service.mark_completed(job.id)

    response = client.get(f"/api/jobs/{job.id}/download", follow_redirects=False)

    assert response.status_code in {302, 307}
    assert response.headers["location"] == f"https://cdn.example.com/media/{job.output_video_path}"


def test_list_job_edits_returns_paginated_history(
    client: TestClient,
    db_session: Session,
    tmp_path,
) -> None:
    storage = StorageService(tmp_path, use_db_lookup=False)
    service = JobService(db_session, storage)
    first = service.create_job(
        JobCreate(source_url="https://www.douyin.com/video/111", voice_id="vi_female_01")
    )
    second = service.create_job(
        JobCreate(source_url="https://www.douyin.com/video/222", voice_id="vi_female_01")
    )
    service.create_edit(
        first.id,
        edit_id="edit-001",
        tool_summary="Video :: Blur/Mask",
        config_json={"blur_original_subtitles": False},
        output_video_path=storage.write_edit_text(first.id, "edit-001", "output_vi_edit.mp4", "edited video"),
        result_url=f"/api/jobs/{first.id}/edits/edit-001/download",
    )
    service.create_edit(
        first.id,
        edit_id="draft-001",
        tool_summary="Video :: Overlay",
        config_json={"overlay_enabled": True},
        output_video_path=None,
        result_url=None,
        is_draft=True,
    )
    service.create_edit(
        second.id,
        edit_id="edit-002",
        tool_summary="Captions :: Style/Position",
        config_json={"burn_subtitle": False},
        output_video_path=storage.write_edit_text(second.id, "edit-002", "output_vi_edit.mp4", "edited video"),
        result_url=f"/api/jobs/{second.id}/edits/edit-002/download",
    )

    response = client.get("/api/jobs/edits?page=1&page_size=10")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total_pages"] == 1
    assert {item["edit_id"] for item in data["items"]} == {"edit-001", "edit-002"}


def test_list_job_edits_supports_search_tool_filter_and_sort(
    client: TestClient,
    db_session: Session,
    tmp_path,
) -> None:
    storage = StorageService(tmp_path, use_db_lookup=False)
    service = JobService(db_session, storage)
    first = service.create_job(
        JobCreate(source_url="https://www.douyin.com/video/111", voice_id="vi_female_01")
    )
    second = service.create_job(
        JobCreate(source_url="https://www.douyin.com/video/222", voice_id="vi_female_01")
    )
    service.create_edit(
        first.id,
        edit_id="edit-101",
        tool_summary="Video :: Trim/Speed",
        config_json={"trim_start_seconds": 1},
        output_video_path=storage.write_edit_text(first.id, "edit-101", "output_vi_edit.mp4", "edited video"),
        result_url=f"/api/jobs/{first.id}/edits/edit-101/download",
    )
    service.create_edit(
        second.id,
        edit_id="edit-202",
        tool_summary="Captions :: Caption editor + Timing editor",
        config_json={"burn_subtitle": True},
        output_video_path=storage.write_edit_text(second.id, "edit-202", "output_vi_edit.mp4", "edited video"),
        result_url=f"/api/jobs/{second.id}/edits/edit-202/download",
    )

    response = client.get("/api/jobs/edits?page=1&page_size=10&search=edit-101&tool=video&sort=oldest")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["edit_id"] == "edit-101"
    assert data["items"][0]["tool_group"] == "Video"
    assert data["items"][0]["tool_options"] == "Trim/Speed"


def test_get_job_edit_detail_returns_saved_config(
    client: TestClient,
    db_session: Session,
    tmp_path,
) -> None:
    storage = StorageService(tmp_path, use_db_lookup=False)
    service = JobService(db_session, storage)
    job = service.create_job(
        JobCreate(source_url="https://www.douyin.com/video/333", voice_id="vi_female_01")
    )
    service.create_edit(
        job.id,
        edit_id="edit-restore-001",
        tool_summary="Video + Captions :: Overlay + Style/Position",
        config_json={
            "overlay_enabled": True,
            "overlay_text": "Demo overlay",
            "overlay_position": "top_right",
            "subtitle_font_size": 26,
        },
        output_video_path=storage.write_edit_text(job.id, "edit-restore-001", "output_vi_edit.mp4", "edited video"),
        result_url=f"/api/jobs/{job.id}/edits/edit-restore-001/download",
    )

    response = client.get(f"/api/jobs/{job.id}/edits/edit-restore-001")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job.id
    assert data["edit_id"] == "edit-restore-001"
    assert data["tool_summary"] == "Video + Captions :: Overlay + Style/Position"
    assert data["config"]["overlay_enabled"] is True
    assert data["config"]["overlay_text"] == "Demo overlay"
    assert data["result_url"] == f"/api/jobs/{job.id}/edits/edit-restore-001/download"
