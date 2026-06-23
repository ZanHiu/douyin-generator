import pytest
from pydantic import ValidationError

from app.schemas.job import JobCreate


def test_job_create_accepts_http_url() -> None:
    payload = JobCreate(source_url="https://www.douyin.com/video/123")

    assert payload.source_url == "https://www.douyin.com/video/123"
    assert payload.voice_id == "banmai"


def test_job_create_rejects_invalid_url() -> None:
    with pytest.raises(ValidationError):
        JobCreate(source_url="not-a-url")
