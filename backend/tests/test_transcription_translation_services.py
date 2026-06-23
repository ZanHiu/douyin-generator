import json

import httpx
import pytest

from app.core.config import settings
from app.services.errors import ProcessingError
from app.services.storage_service import StorageService
from app.services.transcription_service import TranscriptionService
from app.services.translation_service import TranslationService


def test_mock_transcription_writes_normalized_transcript(tmp_path) -> None:
    original_provider = settings.stt_provider
    object.__setattr__(settings, "stt_provider", "mock")
    storage = StorageService(tmp_path)
    try:
        transcript_path = TranscriptionService(storage).transcribe("job-1", "missing-audio.wav")

        transcript = json.loads((tmp_path / "jobs" / "job-1" / "transcript_zh.json").read_text(encoding="utf-8"))
        assert transcript_path.endswith("transcript_zh.json")
        assert transcript["language"] == "zh"
        assert transcript["segments"][0]["text"]
    finally:
        object.__setattr__(settings, "stt_provider", original_provider)


def test_mock_translation_preserves_ids_and_timestamps(tmp_path) -> None:
    original_provider = settings.translation_provider
    object.__setattr__(settings, "translation_provider", "mock")
    storage = StorageService(tmp_path)
    try:
        transcript_path = storage.write_json(
            "job-1",
            "transcript_zh.json",
            {
                "language": "zh",
                "segments": [
                    {"id": 7, "start": 1.2, "end": 3.4, "text": "\u4f60\u597d"},
                ],
            },
        )

        translation_path = TranslationService(storage).translate("job-1", transcript_path)

        translated = json.loads((tmp_path / "jobs" / "job-1" / "transcript_vi.json").read_text(encoding="utf-8"))
        assert translation_path.endswith("transcript_vi.json")
        assert translated[0]["id"] == 7
        assert translated[0]["start"] == 1.2
        assert translated[0]["end"] == 3.4
        assert translated[0]["text_zh"] == "\u4f60\u597d"
        assert translated[0]["text_vi"]
    finally:
        object.__setattr__(settings, "translation_provider", original_provider)


def test_translation_rejects_missing_transcript(tmp_path) -> None:
    with pytest.raises(ProcessingError, match="Missing Chinese transcript"):
        TranslationService(StorageService(tmp_path)).translate("job-1", str(tmp_path / "missing.json"))


def test_openai_transcription_requires_api_key(tmp_path) -> None:
    original_provider = settings.stt_provider
    original_api_key = settings.openai_api_key
    object.__setattr__(settings, "stt_provider", "openai")
    object.__setattr__(settings, "openai_api_key", None)
    try:
        with pytest.raises(ProcessingError, match="OPENAI_API_KEY"):
            TranscriptionService(StorageService(tmp_path)).transcribe("job-1", "audio.wav")
    finally:
        object.__setattr__(settings, "stt_provider", original_provider)
        object.__setattr__(settings, "openai_api_key", original_api_key)


def test_openai_translation_requires_api_key(tmp_path) -> None:
    storage = StorageService(tmp_path)
    transcript_path = storage.write_json(
        "job-1",
        "transcript_zh.json",
        {"language": "zh", "segments": [{"id": 0, "start": 0.0, "end": 1.0, "text": "\u4f60\u597d"}]},
    )
    original_provider = settings.translation_provider
    original_api_key = settings.openai_api_key
    object.__setattr__(settings, "translation_provider", "openai")
    object.__setattr__(settings, "openai_api_key", None)
    try:
        with pytest.raises(ProcessingError, match="OPENAI_API_KEY"):
            TranslationService(storage).translate("job-1", transcript_path)
    finally:
        object.__setattr__(settings, "translation_provider", original_provider)
        object.__setattr__(settings, "openai_api_key", original_api_key)


def test_openrouter_translation_requires_api_key(tmp_path) -> None:
    storage = StorageService(tmp_path)
    transcript_path = storage.write_json(
        "job-1",
        "transcript_zh.json",
        {"language": "zh", "segments": [{"id": 0, "start": 0.0, "end": 1.0, "text": "\u4f60\u597d"}]},
    )
    original_provider = settings.translation_provider
    original_api_key = settings.openrouter_api_key
    object.__setattr__(settings, "translation_provider", "openrouter")
    object.__setattr__(settings, "openrouter_api_key", None)
    try:
        with pytest.raises(ProcessingError, match="OPENROUTER_API_KEY"):
            TranslationService(storage).translate("job-1", transcript_path)
    finally:
        object.__setattr__(settings, "translation_provider", original_provider)
        object.__setattr__(settings, "openrouter_api_key", original_api_key)


def test_unsupported_transcription_provider_fails(tmp_path) -> None:
    original_provider = settings.stt_provider
    object.__setattr__(settings, "stt_provider", "unknown")
    try:
        with pytest.raises(ProcessingError, match="STT provider"):
            TranscriptionService(StorageService(tmp_path)).transcribe("job-1", "audio.wav")
    finally:
        object.__setattr__(settings, "stt_provider", original_provider)


def test_faster_whisper_rejects_missing_audio_before_model_load(tmp_path) -> None:
    original_provider = settings.stt_provider
    object.__setattr__(settings, "stt_provider", "faster_whisper")
    try:
        with pytest.raises(ProcessingError, match="Missing audio file"):
            TranscriptionService(StorageService(tmp_path)).transcribe("job-1", str(tmp_path / "missing.wav"))
    finally:
        object.__setattr__(settings, "stt_provider", original_provider)


def test_openai_transcription_normalization_drops_empty_and_clamps_timestamps() -> None:
    normalized = TranscriptionService._normalize_openai_segments(
        {
            "segments": [
                {"id": 4, "start": -1.0, "end": 1.5, "text": " Ni hao "},
                {"id": 5, "start": 2.0, "end": 1.0, "text": " "},
                {"id": 6, "start": 3.0, "end": 2.5, "text": "Zai jian"},
            ]
        }
    )

    assert normalized == [
        {"id": 4, "start": 0.0, "end": 1.5, "text": "Ni hao"},
        {"id": 6, "start": 3.0, "end": 3.0, "text": "Zai jian"},
    ]


def test_openai_translation_parser_preserves_source_timing() -> None:
    source = [
        {"id": 7, "start": 1.2, "end": 3.4, "text_zh": "ni hao"},
        {"id": 8, "start": 4.0, "end": 5.0, "text_zh": "zai jian"},
    ]
    content = json.dumps(
        {
            "segments": [
                {"id": 7, "start": 99, "end": 100, "text_vi": "Xin chao"},
                {"id": 8, "text_vi": "Tam biet"},
            ]
        }
    )

    translated = TranslationService._parse_openai_compatible_translation_content(content, source)

    assert translated == [
        {"id": 7, "start": 1.2, "end": 3.4, "text_zh": "ni hao", "text_vi": "Xin chao"},
        {"id": 8, "start": 4.0, "end": 5.0, "text_zh": "zai jian", "text_vi": "Tam biet"},
    ]


def test_openai_translation_parser_rejects_missing_segment() -> None:
    source = [{"id": 7, "start": 1.2, "end": 3.4, "text_zh": "ni hao"}]

    with pytest.raises(ValueError, match="missing translated segment"):
        TranslationService._parse_openai_compatible_translation_content('{"segments":[]}', source)


def test_openai_translation_parser_rejects_wrapped_content() -> None:
    source = [{"id": 7, "start": 1.2, "end": 3.4, "text_zh": "ni hao"}]
    content = '<think>reasoning</think>\n{"segments":[{"id":7,"text_vi":"Xin chao"}]}'

    with pytest.raises(json.JSONDecodeError):
        TranslationService._parse_openai_compatible_translation_content(content, source)


def test_ollama_translation_parser_extracts_json_from_wrapped_content() -> None:
    source = [{"id": 7, "start": 1.2, "end": 3.4, "text_zh": "ni hao"}]
    content = '<think>reasoning</think>\n{"segments":[{"id":7,"text_vi":"Xin chao"}]}'

    translated = TranslationService._parse_ollama_translation_content(content, source)

    assert translated == [{"id": 7, "start": 1.2, "end": 3.4, "text_zh": "ni hao", "text_vi": "Xin chao"}]


def test_translation_parser_reads_nested_ollama_message_content() -> None:
    source = [{"id": 7, "start": 1.2, "end": 3.4, "text_zh": "ni hao"}]
    content = json.dumps({"message": {"content": '{"segments":[{"id":7,"text_vi":"Xin chao"}]}'}})

    translated = TranslationService._parse_ollama_translation_content(content, source)

    assert translated == [{"id": 7, "start": 1.2, "end": 3.4, "text_zh": "ni hao", "text_vi": "Xin chao"}]


def test_translation_parser_accepts_ollama_id_map_response() -> None:
    source = [
        {"id": 0, "start": 0.0, "end": 1.0, "text_zh": "ni hao"},
        {"id": 1, "start": 1.0, "end": 2.0, "text_zh": "zai jian"},
    ]
    content = json.dumps({"0": "Xin chao", "1": "Tam biet"})

    translated = TranslationService._parse_ollama_translation_content(content, source)

    assert translated == [
        {"id": 0, "start": 0.0, "end": 1.0, "text_zh": "ni hao", "text_vi": "Xin chao"},
        {"id": 1, "start": 1.0, "end": 2.0, "text_zh": "zai jian", "text_vi": "Tam biet"},
    ]


def test_translation_parser_accepts_ollama_string_list_response() -> None:
    source = [
        {"id": 10, "start": 10.0, "end": 11.0, "text_zh": "ni hao"},
        {"id": 11, "start": 11.0, "end": 12.0, "text_zh": "zai jian"},
    ]
    content = json.dumps({"segments": ["Xin chao", "Tam biet"]})

    translated = TranslationService._parse_ollama_translation_content(content, source)

    assert translated == [
        {"id": 10, "start": 10.0, "end": 11.0, "text_zh": "ni hao", "text_vi": "Xin chao"},
        {"id": 11, "start": 11.0, "end": 12.0, "text_zh": "zai jian", "text_vi": "Tam biet"},
    ]


def test_translation_parser_accepts_ollama_translations_list_response() -> None:
    source = [
        {"id": 10, "start": 10.0, "end": 11.0, "text_zh": "ni hao"},
        {"id": 11, "start": 11.0, "end": 12.0, "text_zh": "zai jian"},
    ]
    content = json.dumps({"translations": ["Xin chao", "Tam biet"]})

    translated = TranslationService._parse_ollama_translation_content(content, source)

    assert translated == [
        {"id": 10, "start": 10.0, "end": 11.0, "text_zh": "ni hao", "text_vi": "Xin chao"},
        {"id": 11, "start": 11.0, "end": 12.0, "text_zh": "zai jian", "text_vi": "Tam biet"},
    ]


def test_translation_parser_accepts_ollama_translations_id_map_response() -> None:
    source = [
        {"id": 20, "start": 20.0, "end": 21.0, "text_zh": "ni hao"},
        {"id": 21, "start": 21.0, "end": 22.0, "text_zh": "zai jian"},
    ]
    content = json.dumps({"translations": {"id_20": "Xin chao", "id_21": "Tam biet"}})

    translated = TranslationService._parse_ollama_translation_content(content, source)

    assert translated == [
        {"id": 20, "start": 20.0, "end": 21.0, "text_zh": "ni hao", "text_vi": "Xin chao"},
        {"id": 21, "start": 21.0, "end": 22.0, "text_zh": "zai jian", "text_vi": "Tam biet"},
    ]


def test_translation_parser_accepts_ollama_single_translation_response() -> None:
    source = [{"id": 10, "start": 10.0, "end": 11.0, "text_zh": "ni shuo de shi zhen de"}]
    content = json.dumps({"id": 10, "translation": "Du ban noi that"})

    translated = TranslationService._parse_ollama_translation_content(content, source)

    assert translated == [
        {
            "id": 10,
            "start": 10.0,
            "end": 11.0,
            "text_zh": "ni shuo de shi zhen de",
            "text_vi": "Du ban noi that",
        }
    ]


def test_ollama_translation_request_uses_local_api(monkeypatch) -> None:
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return httpx.Response(
            200,
            json={"message": {"content": '{"segments":[{"id":7,"text_vi":"Xin chao"}]}'}},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    source = [{"id": 7, "start": 1.2, "end": 3.4, "text_zh": "ni hao"}]

    translated, raw_content = TranslationService()._request_ollama_translation(source)

    assert captured["url"].endswith("/api/chat")
    assert captured["json"]["model"] == settings.ollama_model
    assert captured["json"]["stream"] is False
    assert raw_content == '{"segments":[{"id":7,"text_vi":"Xin chao"}]}'
    assert translated == [{"id": 7, "start": 1.2, "end": 3.4, "text_zh": "ni hao", "text_vi": "Xin chao"}]


def test_openrouter_headers_include_optional_app_metadata() -> None:
    original_referer = settings.openrouter_http_referer
    original_title = settings.openrouter_app_title
    object.__setattr__(settings, "openrouter_http_referer", "http://localhost:5173")
    object.__setattr__(settings, "openrouter_app_title", "DouyinGenerator")
    try:
        assert TranslationService._openrouter_headers() == {
            "HTTP-Referer": "http://localhost:5173",
            "X-OpenRouter-Title": "DouyinGenerator",
        }
    finally:
        object.__setattr__(settings, "openrouter_http_referer", original_referer)
        object.__setattr__(settings, "openrouter_app_title", original_title)


def test_translation_error_details_summarize_cloudflare_html() -> None:
    class FakeProviderError(Exception):
        status_code = 530

    html = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Origin DNS error | roster-pierre-returns-savings.trycloudflare.com | Cloudflare</title>
      </head>
      <body>Cloudflare is currently unable to resolve your requested domain.</body>
    </html>
    status_code=530
    """

    details = TranslationService._openai_compatible_error_details(FakeProviderError(html))

    assert "Cloudflare Origin DNS error from translation provider" in details
    assert "roster-pierre-returns-savings.trycloudflare.com" in details
    assert "status_code=530" in details
    assert "<!DOCTYPE html>" not in details


def test_openrouter_translate_writes_raw_artifacts(tmp_path, monkeypatch) -> None:
    storage = StorageService(tmp_path)
    service = TranslationService(storage)
    transcript_path = storage.write_json(
        "job-1",
        "transcript_zh.json",
        {"language": "zh", "segments": [{"id": 0, "start": 0.0, "end": 1.0, "text": "ni hao"}]},
    )

    def fake_translate(**_kwargs):
        return (
            [{"id": 0, "start": 0.0, "end": 1.0, "text_zh": "ni hao", "text_vi": "Xin chao"}],
            ['{"segments":[{"id":0,"text_vi":"Xin chao"}]}'],
        )

    original_provider = settings.translation_provider
    original_api_key = settings.openrouter_api_key
    object.__setattr__(settings, "translation_provider", "openrouter")
    object.__setattr__(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(service, "_translate_with_openai_compatible_provider", fake_translate)
    try:
        output_path = service.translate("job-1", transcript_path)
    finally:
        object.__setattr__(settings, "translation_provider", original_provider)
        object.__setattr__(settings, "openrouter_api_key", original_api_key)

    translated = json.loads((tmp_path / "jobs" / "job-1" / "transcript_vi.json").read_text(encoding="utf-8"))
    raw = json.loads((tmp_path / "jobs" / "job-1" / "transcript_vi_raw.json").read_text(encoding="utf-8"))
    assert output_path.endswith("transcript_vi.json")
    assert translated[0]["text_vi"] == "Xin chao"
    assert raw["provider"] == "openrouter"
    assert raw["responses"] == ['{"segments":[{"id":0,"text_vi":"Xin chao"}]}']


def test_openrouter_translate_writes_raw_artifact_on_failure(tmp_path, monkeypatch) -> None:
    storage = StorageService(tmp_path)
    service = TranslationService(storage)
    transcript_path = storage.write_json(
        "job-1",
        "transcript_zh.json",
        {"language": "zh", "segments": [{"id": 0, "start": 0.0, "end": 1.0, "text": "ni hao"}]},
    )
    def fake_translate(**kwargs):
        assert kwargs["model"] == "primary/free"
        raise ProcessingError("TRANSLATION_FAILED", "openrouter translation failed: invalid api key")

    original_provider = settings.translation_provider
    original_api_key = settings.openrouter_api_key
    original_model = settings.openrouter_model
    object.__setattr__(settings, "translation_provider", "openrouter")
    object.__setattr__(settings, "openrouter_api_key", "test-key")
    object.__setattr__(settings, "openrouter_model", "primary/free")
    monkeypatch.setattr(service, "_translate_with_openai_compatible_provider", fake_translate)
    try:
        with pytest.raises(ProcessingError, match="invalid api key"):
            service.translate("job-1", transcript_path)
    finally:
        object.__setattr__(settings, "translation_provider", original_provider)
        object.__setattr__(settings, "openrouter_api_key", original_api_key)
        object.__setattr__(settings, "openrouter_model", original_model)

    raw = json.loads((tmp_path / "jobs" / "job-1" / "transcript_vi_raw.json").read_text(encoding="utf-8"))
    assert raw["model"] == "primary/free"
    assert raw["error"] == "openrouter translation failed: invalid api key"


def test_nine_router_translate_writes_raw_artifacts(tmp_path, monkeypatch) -> None:
    storage = StorageService(tmp_path)
    service = TranslationService(storage)
    transcript_path = storage.write_json(
        "job-1",
        "transcript_zh.json",
        {"language": "zh", "segments": [{"id": 0, "start": 0.0, "end": 1.0, "text": "ni hao"}]},
    )

    def fake_translate(**kwargs):
        assert kwargs["model"] == "qwen"
        assert kwargs["api_key"] == "local-9router"
        assert kwargs["base_url"] == "http://localhost:20128/v1"
        assert kwargs["provider_name"] == "nine_router"
        return (
            [{"id": 0, "start": 0.0, "end": 1.0, "text_zh": "ni hao", "text_vi": "Xin chao"}],
            ['{"segments":[{"id":0,"text_vi":"Xin chao"}]}'],
        )

    original_provider = settings.translation_provider
    original_api_key = settings.nine_router_api_key
    original_model = settings.nine_router_model
    original_base_url = settings.nine_router_base_url
    object.__setattr__(settings, "translation_provider", "nine_router")
    object.__setattr__(settings, "nine_router_api_key", None)
    object.__setattr__(settings, "nine_router_model", "qwen")
    object.__setattr__(settings, "nine_router_base_url", "http://localhost:20128/v1")
    monkeypatch.setattr(service, "_translate_with_openai_compatible_provider", fake_translate)
    try:
        output_path = service.translate("job-1", transcript_path)
    finally:
        object.__setattr__(settings, "translation_provider", original_provider)
        object.__setattr__(settings, "nine_router_api_key", original_api_key)
        object.__setattr__(settings, "nine_router_model", original_model)
        object.__setattr__(settings, "nine_router_base_url", original_base_url)

    translated = json.loads((tmp_path / "jobs" / "job-1" / "transcript_vi.json").read_text(encoding="utf-8"))
    raw = json.loads((tmp_path / "jobs" / "job-1" / "transcript_vi_raw.json").read_text(encoding="utf-8"))
    assert output_path.endswith("transcript_vi.json")
    assert translated[0]["text_vi"] == "Xin chao"
    assert raw["provider"] == "nine_router"
    assert raw["model"] == "qwen"
    assert raw["responses"] == ['{"segments":[{"id":0,"text_vi":"Xin chao"}]}']


def test_openrouter_request_retries_same_model_on_rate_limit(monkeypatch) -> None:
    service = TranslationService()
    calls = []
    sleeps = []

    def fake_request(**kwargs):
        calls.append(kwargs["model"])
        if len(calls) == 1:
            raise ProcessingError(
                "TRANSLATION_FAILED",
                "openrouter translation failed: 429 retry_after_seconds': 2",
            )
        return (
            [{"id": 0, "start": 0.0, "end": 1.0, "text_zh": "ni hao", "text_vi": "Xin chao"}],
            '{"segments":[{"id":0,"text_vi":"Xin chao"}]}',
        )

    monkeypatch.setattr(service, "_request_openai_compatible_translation", fake_request)
    monkeypatch.setattr("app.services.translation_service.time.sleep", lambda seconds: sleeps.append(seconds))

    translated, raw = service._request_openai_compatible_translation_with_retry(
        payload=[{"id": 0, "start": 0.0, "end": 1.0, "text_zh": "ni hao"}],
        model="primary/free",
        api_key="test-key",
        base_url="https://openrouter.ai/api/v1",
        timeout_seconds=120,
        provider_name="openrouter",
    )

    assert calls == ["primary/free", "primary/free"]
    assert sleeps == [3.0]
    assert raw == '{"segments":[{"id":0,"text_vi":"Xin chao"}]}'
    assert translated[0]["text_vi"] == "Xin chao"


def test_groq_request_retries_same_model_on_retry_after(monkeypatch) -> None:
    service = TranslationService()
    calls = []
    sleeps = []

    def fake_request(**kwargs):
        calls.append(kwargs["model"])
        if len(calls) == 1:
            raise ProcessingError(
                "TRANSLATION_FAILED",
                "groq translation failed: 429 headers={'retry-after': '4'}",
            )
        return (
            [{"id": 0, "start": 0.0, "end": 1.0, "text_zh": "ni hao", "text_vi": "Xin chao"}],
            '{"segments":[{"id":0,"text_vi":"Xin chao"}]}',
        )

    monkeypatch.setattr(service, "_request_openai_compatible_translation", fake_request)
    monkeypatch.setattr("app.services.translation_service.time.sleep", lambda seconds: sleeps.append(seconds))

    translated, raw = service._request_openai_compatible_translation_with_retry(
        payload=[{"id": 0, "start": 0.0, "end": 1.0, "text_zh": "ni hao"}],
        model="qwen/qwen3-32b",
        api_key="test-key",
        base_url="https://api.groq.com/openai/v1",
        timeout_seconds=120,
        provider_name="groq",
    )

    assert calls == ["qwen/qwen3-32b", "qwen/qwen3-32b"]
    assert sleeps == [5.0]
    assert raw == '{"segments":[{"id":0,"text_vi":"Xin chao"}]}'
    assert translated[0]["text_vi"] == "Xin chao"


def test_groq_request_uses_token_reset_delay_when_retry_after_missing(monkeypatch) -> None:
    service = TranslationService()
    calls = []
    sleeps = []

    def fake_request(**kwargs):
        calls.append(kwargs["model"])
        if len(calls) == 1:
            raise ProcessingError(
                "TRANSLATION_FAILED",
                "groq translation failed: 429 headers={'x-ratelimit-reset-tokens': '2s'}",
            )
        return (
            [{"id": 0, "start": 0.0, "end": 1.0, "text_zh": "ni hao", "text_vi": "Xin chao"}],
            '{"segments":[{"id":0,"text_vi":"Xin chao"}]}',
        )

    monkeypatch.setattr(service, "_request_openai_compatible_translation", fake_request)
    monkeypatch.setattr("app.services.translation_service.time.sleep", lambda seconds: sleeps.append(seconds))

    service._request_openai_compatible_translation_with_retry(
        payload=[{"id": 0, "start": 0.0, "end": 1.0, "text_zh": "ni hao"}],
        model="qwen/qwen3-32b",
        api_key="test-key",
        base_url="https://api.groq.com/openai/v1",
        timeout_seconds=120,
        provider_name="groq",
    )

    assert calls == ["qwen/qwen3-32b", "qwen/qwen3-32b"]
    assert sleeps == [3.0]


def test_ollama_translation_writes_raw_response_on_parse_failure(tmp_path, monkeypatch) -> None:
    storage = StorageService(tmp_path)
    service = TranslationService(storage)

    def fake_request(_batch):
        return '{"not_segments":[]}'

    monkeypatch.setattr(service, "_request_ollama_translation_content", fake_request)

    with pytest.raises(ProcessingError, match="Ollama translation JSON"):
        service._ollama_translate("job-1", [{"id": 7, "start": 1.2, "end": 3.4, "text": "ni hao"}])

    raw = json.loads((tmp_path / "jobs" / "job-1" / "transcript_vi_raw.json").read_text(encoding="utf-8"))
    assert raw["provider"] == "ollama"
    assert raw["responses"] == ['{"not_segments":[]}']
    assert raw["error"] == "missing translated segment id 7"


def test_ollama_batch_repair_retries_missing_segments(monkeypatch) -> None:
    service = TranslationService()
    batch = [
        {"id": 10, "start": 10.0, "end": 11.0, "text_zh": "shi"},
        {"id": 11, "start": 11.0, "end": 12.0, "text_zh": "hao"},
    ]
    calls = []

    def fake_request(payload):
        calls.append([item["id"] for item in payload])
        return json.dumps({str(item["id"]): f"Ban dich {item['id']}" for item in payload})

    monkeypatch.setattr(service, "_request_ollama_translation_content", fake_request)
    raw_responses = []

    repaired = service._parse_ollama_batch_with_repair(batch, '{"10":"Ban dich 10"}', raw_responses)

    assert calls == [[10], [11]]
    assert repaired == [
        {"id": 10, "start": 10.0, "end": 11.0, "text_zh": "shi", "text_vi": "Ban dich 10"},
        {"id": 11, "start": 11.0, "end": 12.0, "text_zh": "hao", "text_vi": "Ban dich 11"},
    ]


def test_ollama_batch_repair_falls_back_when_single_segment_fails(monkeypatch) -> None:
    service = TranslationService()
    batch = [
        {"id": 10, "start": 10.0, "end": 11.0, "text_zh": "shi"},
        {"id": 11, "start": 11.0, "end": 12.0, "text_zh": "hao"},
    ]

    def fake_request(_payload):
        return "{}"

    monkeypatch.setattr(service, "_request_ollama_translation_content", fake_request)
    raw_responses = []

    repaired = service._parse_ollama_batch_with_repair(batch, '{"10":"Ban dich 10"}', raw_responses)

    assert repaired[-1] == {
        "id": 11,
        "start": 11.0,
        "end": 12.0,
        "text_zh": "hao",
        "text_vi": "Could not translate this segment.",
    }
    assert any(isinstance(item, dict) and item.get("fallback") for item in raw_responses)


def test_translation_payload_chunking() -> None:
    payload = [{"id": index} for index in range(5)]

    chunks = TranslationService._chunk_payload(payload, 2)

    assert chunks == [[{"id": 0}, {"id": 1}], [{"id": 2}, {"id": 3}], [{"id": 4}]]
