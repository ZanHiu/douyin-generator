import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[3]

load_dotenv(REPO_ROOT / ".env")


def resolve_from_repo(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def normalize_samesite(value: str | None) -> str:
    normalized = (value or "lax").strip().lower()
    if normalized in {"lax", "strict", "none"}:
        return normalized
    return "lax"

@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://douyin:douyin@localhost:5432/douyin_generator",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    storage_backend: str = os.getenv("STORAGE_BACKEND", "local")
    storage_root: Path = resolve_from_repo(os.getenv("STORAGE_ROOT", "./storage"))
    storage_prefix: str = os.getenv("STORAGE_PREFIX", "").strip("/")
    storage_bucket: str | None = os.getenv("STORAGE_BUCKET") or None
    storage_endpoint_url: str | None = os.getenv("STORAGE_ENDPOINT_URL") or None
    storage_region: str | None = os.getenv("STORAGE_REGION") or None
    storage_access_key: str | None = os.getenv("STORAGE_ACCESS_KEY") or None
    storage_secret_key: str | None = os.getenv("STORAGE_SECRET_KEY") or None
    storage_secure: bool = os.getenv("STORAGE_SECURE", "true").lower() == "true"
    storage_public_url_base: str | None = os.getenv("STORAGE_PUBLIC_URL_BASE") or None
    storage_presign_expiry_seconds: int = int(os.getenv("STORAGE_PRESIGN_EXPIRY_SECONDS", "3600"))
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    frontend_origins: list[str] = field(
        default_factory=lambda: parse_csv(os.getenv("FRONTEND_ORIGINS"))
        or [os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")]
    )
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "change-me-please")
    auth_cookie_name: str = os.getenv("AUTH_COOKIE_NAME", "douyin_session")
    auth_session_hours: int = int(os.getenv("AUTH_SESSION_HOURS", "168"))
    auth_cookie_secure: bool = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
    auth_cookie_samesite: str = normalize_samesite(os.getenv("AUTH_COOKIE_SAMESITE", "lax"))
    auth_cookie_domain: str | None = os.getenv("AUTH_COOKIE_DOMAIN") or None
    queue_stale_job_minutes: int = int(os.getenv("QUEUE_STALE_JOB_MINUTES", "20"))
    queue_cancellation_grace_seconds: int = int(os.getenv("QUEUE_CANCELLATION_GRACE_SECONDS", "30"))
    mock_fail_stage: str | None = os.getenv("MOCK_FAIL_STAGE") or None
    ytdlp_bin: str = os.getenv("YTDLP_BIN", "yt-dlp")
    ytdlp_cookies_file: str | None = os.getenv("YTDLP_COOKIES_FILE") or None
    ffmpeg_bin: str = os.getenv("FFMPEG_BIN", "ffmpeg")
    ffprobe_bin: str = os.getenv("FFPROBE_BIN", "ffprobe")
    max_video_duration_seconds: int = int(os.getenv("MAX_VIDEO_DURATION_SECONDS", "180"))
    max_video_file_mb: int = int(os.getenv("MAX_VIDEO_FILE_MB", "200"))
    stt_provider: str = os.getenv("STT_PROVIDER", "mock")
    translation_provider: str = os.getenv("TRANSLATION_PROVIDER", "mock")
    tts_provider: str = os.getenv("TTS_PROVIDER", "mock")
    tts_sample_rate: int = int(os.getenv("TTS_SAMPLE_RATE", "16000"))
    tts_poll_attempts: int = int(os.getenv("TTS_POLL_ATTEMPTS", "20"))
    tts_poll_interval_seconds: float = float(os.getenv("TTS_POLL_INTERVAL_SECONDS", "1.0"))
    voice_volume_multiplier: float = float(os.getenv("VOICE_VOLUME_MULTIPLIER", "2.0"))
    mixed_voice_volume_multiplier: float = float(os.getenv("MIXED_VOICE_VOLUME_MULTIPLIER", "1.0"))
    original_audio_volume_multiplier: float = float(os.getenv("ORIGINAL_AUDIO_VOLUME_MULTIPLIER", "0.18"))
    voice_loudnorm_target_i: float = float(os.getenv("VOICE_LOUDNORM_TARGET_I", "-14.0"))
    voice_loudnorm_target_tp: float = float(os.getenv("VOICE_LOUDNORM_TARGET_TP", "-1.5"))
    voice_loudnorm_target_lra: float = float(os.getenv("VOICE_LOUDNORM_TARGET_LRA", "11.0"))
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    transcription_model: str = os.getenv("TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")
    translation_model: str = os.getenv("TRANSLATION_MODEL", "gpt-4o-mini")
    openai_request_timeout_seconds: float = float(os.getenv("OPENAI_REQUEST_TIMEOUT_SECONDS", "120"))
    openai_translation_batch_size: int = int(os.getenv("OPENAI_TRANSLATION_BATCH_SIZE", "20"))
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY") or None
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "qwen/qwen3-next-80b-a3b-instruct:free")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    openrouter_request_timeout_seconds: float = float(os.getenv("OPENROUTER_REQUEST_TIMEOUT_SECONDS", "120"))
    openrouter_translation_batch_size: int = int(os.getenv("OPENROUTER_TRANSLATION_BATCH_SIZE", "120"))
    openrouter_rate_limit_retry_attempts: int = int(os.getenv("OPENROUTER_RATE_LIMIT_RETRY_ATTEMPTS", "8"))
    openrouter_rate_limit_sleep_seconds: float = float(os.getenv("OPENROUTER_RATE_LIMIT_SLEEP_SECONDS", "60"))
    openrouter_http_referer: str | None = os.getenv("OPENROUTER_HTTP_REFERER") or None
    openrouter_app_title: str = os.getenv("OPENROUTER_APP_TITLE", "DouyinGenerator")
    nine_router_api_key: str | None = os.getenv("NINE_ROUTER_API_KEY") or None
    nine_router_model: str = os.getenv("NINE_ROUTER_MODEL", "qwen")
    nine_router_base_url: str = os.getenv("NINE_ROUTER_BASE_URL", "http://localhost:20128/v1")
    nine_router_request_timeout_seconds: float = float(os.getenv("NINE_ROUTER_REQUEST_TIMEOUT_SECONDS", "180"))
    nine_router_translation_batch_size: int = int(os.getenv("NINE_ROUTER_TRANSLATION_BATCH_SIZE", "120"))
    groq_api_key: str | None = os.getenv("GROQ_API_KEY") or None
    groq_model: str = os.getenv("GROQ_MODEL", "qwen/qwen3-32b")
    groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    groq_request_timeout_seconds: float = float(os.getenv("GROQ_REQUEST_TIMEOUT_SECONDS", "120"))
    groq_translation_batch_size: int = int(os.getenv("GROQ_TRANSLATION_BATCH_SIZE", "10"))
    groq_batch_sleep_seconds: float = float(os.getenv("GROQ_BATCH_SLEEP_SECONDS", "15"))
    groq_rate_limit_retry_attempts: int = int(os.getenv("GROQ_RATE_LIMIT_RETRY_ATTEMPTS", "4"))
    groq_rate_limit_sleep_seconds: float = float(os.getenv("GROQ_RATE_LIMIT_SLEEP_SECONDS", "20"))
    whisper_model: str = os.getenv("WHISPER_MODEL", "small")
    whisper_device: str = os.getenv("WHISPER_DEVICE", "cpu")
    whisper_compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    ollama_request_timeout_seconds: float = float(os.getenv("OLLAMA_REQUEST_TIMEOUT_SECONDS", "180"))
    ollama_translation_batch_size: int = int(os.getenv("OLLAMA_TRANSLATION_BATCH_SIZE", "10"))
    fpt_ai_api_key: str | None = os.getenv("FPT_AI_API_KEY") or None
    fpt_ai_voice_id: str = os.getenv("FPT_AI_VOICE_ID", "banmai")
    fpt_ai_speed: str = os.getenv("FPT_AI_SPEED", "0")
    fpt_ai_format: str = os.getenv("FPT_AI_FORMAT", "mp3")
    fpt_ai_tts_url: str = os.getenv("FPT_AI_TTS_URL", "https://api.fpt.ai/hmi/tts/v5")


settings = Settings()
