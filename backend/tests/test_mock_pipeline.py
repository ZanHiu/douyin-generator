from collections.abc import Generator
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models import Job
from app.schemas.job import JobCreate
from app.core.config import settings
from app.services.job_service import JobService
from app.services.mock_pipeline import MockPipeline
from app.services.storage_service import StorageService


class FakeVideoResolver:
    def __init__(self, storage: StorageService) -> None:
        self.storage = storage

    def fetch(self, job_id: str, source_url: str) -> tuple[str, str]:
        input_path = self.storage.write_text(job_id, "input.mp4", "mock video")
        metadata_path = self.storage.write_json(
            job_id,
            "metadata.json",
            {
                "source_url": source_url,
                "platform": "douyin",
                "duration_seconds": 42.0,
                "width": 1080,
                "height": 1920,
            },
        )
        return input_path, metadata_path


class FakeAudioExtractor:
    def __init__(self, storage: StorageService) -> None:
        self.storage = storage

    def extract(self, job_id: str, input_video_path: str) -> str:
        return self.storage.write_text(job_id, "audio.wav", "mock audio")


class FakeRenderer:
    def __init__(self, storage: StorageService) -> None:
        self.storage = storage

    def render(
        self,
        job_id: str,
        input_video_path: str,
        tts_audio_path: str,
        subtitle_path: str,
        original_audio_path: str | None = None,
        mix_original_audio: bool = False,
        burn_subtitle: bool = True,
        subtitle_font_size: int = 18,
        subtitle_position: str = "bottom",
        subtitle_text_color: str = "#FFFFFF",
    ) -> str:
        assert original_audio_path
        assert mix_original_audio is False
        assert burn_subtitle is True
        assert subtitle_font_size == 18
        assert subtitle_position == "bottom"
        assert subtitle_text_color == "#FFFFFF"
        return self.storage.write_text(job_id, "output_vi.mp4", "mock rendered video")


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_job_service_creates_queued_job(db_session: Session, tmp_path) -> None:
    storage = StorageService(tmp_path, use_db_lookup=False)
    service = JobService(db_session, storage)

    job = service.create_job(
        JobCreate(
            source_url="https://www.tiktok.com/@demo/video/123",
            voice_id="vi_female_01",
            burn_subtitle=True,
            mix_original_audio=False,
        )
    )

    assert job.id
    assert job.status == "queued"
    assert job.stage == "created"
    assert job.platform == "tiktok"
    assert job.storage_dir
    assert job.id[:8] in job.storage_dir
    assert "_job_" in job.storage_dir
    assert len(job.logs) == 1
    assert (tmp_path / "jobs").exists()
    assert (tmp_path / "jobs" / storage.build_job_dir_name(job.id, job.platform, job.created_at)).exists()
    assert (tmp_path / "jobs" / storage.build_job_dir_name(job.id, job.platform, job.created_at) / "job_manifest.json").exists()


def test_mock_pipeline_completes_job_and_writes_artifacts(
    db_session: Session,
    tmp_path,
) -> None:
    original_stt_provider = settings.stt_provider
    original_translation_provider = settings.translation_provider
    original_tts_provider = settings.tts_provider
    object.__setattr__(settings, "stt_provider", "mock")
    object.__setattr__(settings, "translation_provider", "mock")
    object.__setattr__(settings, "tts_provider", "mock")
    storage = StorageService(tmp_path, use_db_lookup=False)
    service = JobService(db_session, storage)
    try:
        job = service.create_job(
            JobCreate(
                source_url="https://www.douyin.com/video/123",
                voice_id="vi_female_01",
                burn_subtitle=True,
                mix_original_audio=False,
            )
        )

        MockPipeline(
            service,
            storage,
            video_resolver=FakeVideoResolver(storage),
            audio_extractor=FakeAudioExtractor(storage),
            renderer=FakeRenderer(storage),
        ).run(job.id)

        completed_job = db_session.get(Job, job.id)
        assert completed_job is not None
        assert completed_job.status == "completed"
        assert completed_job.progress == 100
        assert completed_job.result_url == f"/api/jobs/{job.id}/download"
        assert completed_job.subtitle_url == f"/api/jobs/{job.id}/subtitles"
        assert completed_job.input_video_path
        assert completed_job.audio_path
        assert completed_job.transcript_zh_path
        assert completed_job.transcript_vi_path
        assert completed_job.subtitle_path
        assert completed_job.tts_audio_path
        assert completed_job.output_video_path
        job_dir = Path(completed_job.storage_dir)
        assert (job_dir / "job_manifest.json").exists()
        manifest = json.loads((job_dir / "job_manifest.json").read_text(encoding="utf-8"))
        assert manifest["job_id"] == job.id
        assert manifest["status"] == "completed"
        assert (job_dir / "input.mp4").exists()
        assert (job_dir / "audio.wav").exists()
        assert (job_dir / "subtitles_vi.srt").exists()
        assert (job_dir / "tts" / "000.wav").exists()
        assert (job_dir / "voice_vi.wav").exists()
        assert (job_dir / "output_vi.mp4").exists()
        assert completed_job.final_config_json is not None
        assert completed_job.final_config_json["burn_subtitle"] is True
    finally:
        object.__setattr__(settings, "stt_provider", original_stt_provider)
        object.__setattr__(settings, "translation_provider", original_translation_provider)
        object.__setattr__(settings, "tts_provider", original_tts_provider)


def test_mock_pipeline_stops_when_job_is_cancel_requested(
    db_session: Session,
    tmp_path,
) -> None:
    original_stt_provider = settings.stt_provider
    original_translation_provider = settings.translation_provider
    original_tts_provider = settings.tts_provider
    object.__setattr__(settings, "stt_provider", "mock")
    object.__setattr__(settings, "translation_provider", "mock")
    object.__setattr__(settings, "tts_provider", "mock")
    storage = StorageService(tmp_path, use_db_lookup=False)
    service = JobService(db_session, storage)
    try:
        job = service.create_job(
            JobCreate(
                source_url="https://www.douyin.com/video/456",
                voice_id="vi_female_01",
                burn_subtitle=True,
                mix_original_audio=False,
            )
        )
        service.request_cancel(job.id)

        with pytest.raises(RuntimeError, match="Job cancelled"):
            MockPipeline(
                service,
                storage,
                video_resolver=FakeVideoResolver(storage),
                audio_extractor=FakeAudioExtractor(storage),
                renderer=FakeRenderer(storage),
            ).run(job.id)

        cancelled_job = db_session.get(Job, job.id)
        assert cancelled_job is not None
        assert cancelled_job.status == "cancelled"
        assert cancelled_job.progress == 0
    finally:
        object.__setattr__(settings, "stt_provider", original_stt_provider)
        object.__setattr__(settings, "translation_provider", original_translation_provider)
        object.__setattr__(settings, "tts_provider", original_tts_provider)
