import wave

import httpx
import pytest

from app.core.config import settings
from app.services.errors import ProcessingError
from app.services.storage_service import StorageService
from app.services.tts_service import TTSService


def test_mock_tts_generates_segment_wavs_and_aligned_voice(tmp_path) -> None:
    original_provider = settings.tts_provider
    object.__setattr__(settings, "tts_provider", "mock")
    storage = StorageService(tmp_path)
    try:
        transcript_path = storage.write_json(
            "job-1",
            "transcript_vi.json",
            [
                {
                    "id": 0,
                    "start": 0.0,
                    "end": 2.4,
                    "text_vi": "Xin chao moi nguoi.",
                },
                {
                    "id": 1,
                    "start": 2.5,
                    "end": 5.0,
                    "text_vi": "Cach lam nay rat don gian.",
                },
            ],
        )

        voice_path = TTSService(storage).generate_voice("job-1", transcript_path)

        assert voice_path.endswith("voice_vi.wav")
        assert (tmp_path / "jobs" / "job-1" / "tts" / "000.wav").exists()
        assert (tmp_path / "jobs" / "job-1" / "tts" / "001.wav").exists()

        with wave.open(voice_path, "rb") as wav_file:
            assert wav_file.getnchannels() == 1
            assert wav_file.getsampwidth() == 2
            assert wav_file.getframerate() == 16000
            assert wav_file.getnframes() == 80000
    finally:
        object.__setattr__(settings, "tts_provider", original_provider)


def test_mock_tts_rejects_missing_transcript(tmp_path) -> None:
    with pytest.raises(ProcessingError, match="Missing Vietnamese transcript"):
        TTSService(StorageService(tmp_path)).generate_voice("job-1", str(tmp_path / "missing.json"))


def test_mock_tts_rejects_empty_text(tmp_path) -> None:
    original_provider = settings.tts_provider
    object.__setattr__(settings, "tts_provider", "mock")
    storage = StorageService(tmp_path)
    try:
        transcript_path = storage.write_json(
            "job-1",
            "transcript_vi.json",
            [{"id": 0, "start": 0.0, "end": 1.0, "text_vi": ""}],
        )

        with pytest.raises(ProcessingError, match="No Vietnamese segments"):
            TTSService(storage).generate_voice("job-1", transcript_path)
    finally:
        object.__setattr__(settings, "tts_provider", original_provider)


def test_fpt_tts_requires_api_key(tmp_path) -> None:
    storage = StorageService(tmp_path)
    transcript_path = storage.write_json(
        "job-1",
        "transcript_vi.json",
        [{"id": 0, "start": 0.0, "end": 1.0, "text_vi": "Xin chao."}],
    )
    original_provider = settings.tts_provider
    original_api_key = settings.fpt_ai_api_key
    object.__setattr__(settings, "tts_provider", "fpt_ai")
    object.__setattr__(settings, "fpt_ai_api_key", None)
    try:
        with pytest.raises(ProcessingError, match="FPT_AI_API_KEY"):
            TTSService(storage).generate_voice("job-1", transcript_path)
    finally:
        object.__setattr__(settings, "tts_provider", original_provider)
        object.__setattr__(settings, "fpt_ai_api_key", original_api_key)


def test_fpt_audio_url_extraction_supports_known_keys() -> None:
    service = TTSService()

    for key in ("async", "async_url", "url"):
        response = httpx.Response(200, json={key: "https://example.com/audio.mp3"})
        assert service._extract_fpt_audio_url(response) == "https://example.com/audio.mp3"


def test_fpt_audio_url_extraction_accepts_zero_error_string() -> None:
    response = httpx.Response(200, json={"error": "0", "async": "https://example.com/audio.mp3"})

    assert TTSService()._extract_fpt_audio_url(response) == "https://example.com/audio.mp3"


def test_fpt_audio_url_extraction_rejects_nonzero_error() -> None:
    response = httpx.Response(200, json={"error": 1, "message": "Invalid api key"})

    with pytest.raises(ProcessingError, match="Invalid api key"):
        TTSService()._extract_fpt_audio_url(response)


def test_fpt_voice_resolution_uses_config_for_generic_voice() -> None:
    original_voice = settings.fpt_ai_voice_id
    object.__setattr__(settings, "fpt_ai_voice_id", "banmai")
    try:
        assert TTSService._resolve_fpt_voice_id("vi_female_01") == "banmai"
        assert TTSService._resolve_fpt_voice_id("leminh") == "leminh"
    finally:
        object.__setattr__(settings, "fpt_ai_voice_id", original_voice)


def test_fpt_audio_extension_uses_configured_format() -> None:
    original_format = settings.fpt_ai_format
    try:
        object.__setattr__(settings, "fpt_ai_format", "mp3")
        assert TTSService._resolve_fpt_audio_extension() == ".mp3"

        object.__setattr__(settings, "fpt_ai_format", "wav")
        assert TTSService._resolve_fpt_audio_extension() == ".source.wav"
    finally:
        object.__setattr__(settings, "fpt_ai_format", original_format)


def test_fpt_audio_extension_rejects_unknown_format() -> None:
    original_format = settings.fpt_ai_format
    object.__setattr__(settings, "fpt_ai_format", "ogg")
    try:
        with pytest.raises(ProcessingError, match="FPT_AI_FORMAT"):
            TTSService._resolve_fpt_audio_extension()
    finally:
        object.__setattr__(settings, "fpt_ai_format", original_format)


def test_fpt_text_normalization_pads_short_text() -> None:
    assert TTSService._normalize_fpt_text("A") == "A..."
    assert TTSService._normalize_fpt_text("Um") == "Um..."
    assert TTSService._normalize_fpt_text(" Xin   chao ") == "Xin chao"
    assert TTSService._normalize_fpt_text("   ") == ""
