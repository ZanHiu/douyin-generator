import pytest

from app.services.errors import ProcessingError
from app.services.storage_service import StorageService
from app.services.subtitle_service import SubtitleService


def test_format_timestamp() -> None:
    assert SubtitleService.format_timestamp(0) == "00:00:00,000"
    assert SubtitleService.format_timestamp(2.4) == "00:00:02,400"
    assert SubtitleService.format_timestamp(65.1234) == "00:01:05,123"
    assert SubtitleService.format_timestamp(3661.999) == "01:01:01,999"


def test_generate_srt_from_translated_segments(tmp_path) -> None:
    storage = StorageService(tmp_path)
    transcript_path = storage.write_json(
        "job-1",
        "transcript_vi.json",
        [
            {
                "id": 1,
                "start": 2.5,
                "end": 5.0,
                "text_zh": "这个方法很简单。",
                "text_vi": "Cach lam nay rat don gian.",
            },
            {
                "id": 0,
                "start": 0.0,
                "end": 2.4,
                "text_zh": "大家好，今天我们来做一道菜。",
                "text_vi": "Xin chao moi nguoi.",
            },
        ],
    )

    subtitle_path = SubtitleService(storage).generate_srt("job-1", transcript_path)
    content = (tmp_path / "jobs" / "job-1" / "subtitles_vi.srt").read_text(encoding="utf-8")

    assert subtitle_path.endswith("subtitles_vi.srt")
    assert content == (
        "1\n"
        "00:00:00,000 --> 00:00:02,400\n"
        "Xin chao moi nguoi.\n\n"
        "2\n"
        "00:00:02,500 --> 00:00:05,000\n"
        "Cach lam nay rat don gian.\n"
    )


def test_generate_srt_rejects_missing_transcript(tmp_path) -> None:
    with pytest.raises(ProcessingError, match="Missing Vietnamese transcript"):
        SubtitleService(StorageService(tmp_path)).generate_srt("job-1", str(tmp_path / "missing.json"))


def test_generate_srt_rejects_empty_text(tmp_path) -> None:
    storage = StorageService(tmp_path)
    transcript_path = storage.write_json(
        "job-1",
        "transcript_vi.json",
        [{"id": 0, "start": 0.0, "end": 1.0, "text_vi": ""}],
    )

    with pytest.raises(ProcessingError, match="No Vietnamese segments"):
        SubtitleService(storage).generate_srt("job-1", transcript_path)


def test_write_srt_from_segments_supports_caption_editor_and_timing_editor(tmp_path) -> None:
    storage = StorageService(tmp_path)
    service = SubtitleService(storage)

    subtitle_path = service.write_srt_from_segments(
        "job-1",
        "edit_subtitles_vi.srt",
        [
            {"id": 0, "start": 0.1, "end": 2.7, "text_vi": "Xin chao tat ca moi nguoi", "text_zh": "ni hao"},
            {"id": 1, "start": 2.8, "end": 4.4, "text_vi": "Lam theo cach nay", "text_zh": "zheyang zuo"},
        ],
    )

    content = (tmp_path / "jobs" / "job-1" / "edit_subtitles_vi.srt").read_text(encoding="utf-8")
    assert subtitle_path.endswith("edit_subtitles_vi.srt")
    assert "00:00:00,100 --> 00:00:02,700" in content
    assert "Xin chao tat ca moi nguoi" in content
