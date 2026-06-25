from typing import Literal
from urllib.parse import urlparse
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

JobStatus = Literal["queued", "processing", "cancelling", "completed", "failed", "cancelled"]
JobSort = Literal["newest", "oldest", "progress"]
JobEditSort = Literal["newest", "oldest"]
JobEditToolFilter = Literal["all", "video", "audio", "captions"]
OverlayPosition = Literal[
    "top_left",
    "top_center",
    "top_right",
    "bottom_left",
    "bottom_center",
    "bottom_right",
    "custom",
]


class BlurMaskItem(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    enabled: bool = True
    x_ratio: float = Field(default=0.0, ge=0.0, le=0.95)
    y_ratio: float = Field(default=0.78, ge=0.0, le=0.95)
    width_ratio: float = Field(default=1.0, ge=0.05, le=1.0)
    height_ratio: float = Field(default=0.22, ge=0.05, le=0.45)
    strength: int = Field(default=11, ge=2, le=11)

    @model_validator(mode="after")
    def validate_bounds(self) -> "BlurMaskItem":
        if self.x_ratio + self.width_ratio > 1.0001:
            raise ValueError("Blur region width exceeds the video bounds.")
        if self.y_ratio + self.height_ratio > 1.0001:
            raise ValueError("Blur region height exceeds the video bounds.")
        return self


class OverlayItem(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    enabled: bool = True
    text: str = Field(default="", max_length=160)
    position: OverlayPosition = "top_right"
    x_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    y_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    font_size: int = Field(default=18, ge=14, le=72)
    text_color: str = "#FFFFFF"

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("text_color")
    @classmethod
    def validate_text_color(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 7 or not normalized.startswith("#"):
            raise ValueError("Overlay text color must be a hex color like #FFFFFF.")
        try:
            int(normalized[1:], 16)
        except ValueError as exc:
            raise ValueError("Overlay text color must be a valid hex color.") from exc
        return normalized


class JobSubtitleSegment(BaseModel):
    id: int
    start: float = Field(ge=0.0, le=180.0)
    end: float = Field(ge=0.0, le=180.0)
    text_vi: str = Field(default="", max_length=500)
    text_zh: str | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "JobSubtitleSegment":
        if self.end < self.start:
            raise ValueError("Subtitle segment end must be greater than or equal to start.")
        return self


class JobCreate(BaseModel):
    source_url: str = Field(min_length=1)
    voice_id: str = "banmai"
    burn_subtitle: bool = True
    mix_original_audio: bool = False

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme == "upload" and (parsed.netloc or parsed.path):
            return value
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Invalid URL.")
        hostname = (parsed.hostname or "").lower()
        allowed_hosts = (
            "douyin.com",
            "iesdouyin.com",
            "tiktok.com",
            "vm.tiktok.com",
            "vt.tiktok.com",
        )
        if not any(hostname == host or hostname.endswith(f".{host}") for host in allowed_hosts):
            raise ValueError("Only Douyin and TikTok URLs are supported in this MVP.")
        return value


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int
    stage: str | None
    error_message: str | None
    result_url: str | None
    subtitle_url: str | None


class JobEditRenderRequest(BaseModel):
    trim_start_seconds: float = Field(default=0.0, ge=0.0, le=180.0)
    trim_end_seconds: float | None = Field(default=None, ge=0.0, le=180.0)
    playback_speed: float = Field(default=1.0, ge=0.5, le=2.0)
    blur_original_subtitles: bool = False
    blur_x_ratio: float = Field(default=0.0, ge=0.0, le=0.95)
    blur_y_ratio: float = Field(default=0.78, ge=0.0, le=0.95)
    blur_width_ratio: float = Field(default=1.0, ge=0.05, le=1.0)
    blur_height_ratio: float = Field(default=0.22, ge=0.05, le=0.45)
    blur_strength: int = Field(default=11, ge=2, le=11)
    blur_masks: list[BlurMaskItem] | None = None
    voice_volume_percent: int = Field(default=100, ge=0, le=200)
    original_volume_percent: int = Field(default=35, ge=0, le=200)
    burn_audio: bool = True
    burn_original_audio: bool = True
    burn_subtitle: bool = True
    subtitle_font_size: int = Field(default=18, ge=14, le=48)
    subtitle_position: Literal["bottom", "lower_third", "top"] = "bottom"
    subtitle_text_color: str = "#FFFFFF"
    subtitle_segments: list[JobSubtitleSegment] | None = None
    overlay_enabled: bool = False
    overlay_text: str = Field(default="", max_length=160)
    overlay_position: OverlayPosition = "top_right"
    overlay_x_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    overlay_y_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    overlay_font_size: int = Field(default=18, ge=14, le=72)
    overlay_text_color: str = "#FFFFFF"
    overlays: list[OverlayItem] | None = None

    @field_validator("subtitle_text_color")
    @classmethod
    def validate_subtitle_text_color(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 7 or not normalized.startswith("#"):
            raise ValueError("Subtitle text color must be a hex color like #FFFFFF.")
        try:
            int(normalized[1:], 16)
        except ValueError as exc:
            raise ValueError("Subtitle text color must be a valid hex color.") from exc
        return normalized

    @field_validator("overlay_text_color")
    @classmethod
    def validate_overlay_text_color(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 7 or not normalized.startswith("#"):
            raise ValueError("Overlay text color must be a hex color like #FFFFFF.")
        try:
            int(normalized[1:], 16)
        except ValueError as exc:
            raise ValueError("Overlay text color must be a valid hex color.") from exc
        return normalized

    @field_validator("overlay_text")
    @classmethod
    def normalize_overlay_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_trim_range(self) -> "JobEditRenderRequest":
        if self.trim_end_seconds is not None and self.trim_end_seconds <= self.trim_start_seconds:
            raise ValueError("Trim end must be greater than trim start.")
        if self.blur_x_ratio + self.blur_width_ratio > 1.0001:
            raise ValueError("Blur region width exceeds the video bounds.")
        if self.blur_y_ratio + self.blur_height_ratio > 1.0001:
            raise ValueError("Blur region height exceeds the video bounds.")
        return self


class JobEditRenderResponse(BaseModel):
    job_id: str
    edit_id: str
    result_url: str


class JobEditorStateResponse(BaseModel):
    job_id: str
    subtitle_segments: list[JobSubtitleSegment]
    render_config: dict


class JobEditDetailResponse(BaseModel):
    edit_id: str
    job_id: str
    version_number: int | None = None
    tool_summary: str
    config: dict
    result_url: str
    created_at: datetime | None
    updated_at: datetime | None


class JobEditListItem(BaseModel):
    edit_id: str
    job_id: str
    version_number: int | None = None
    tool_group: str
    tool_options: str
    result_url: str
    created_at: datetime | None
    updated_at: datetime | None


class JobEditListResponse(BaseModel):
    items: list[JobEditListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class JobListItem(BaseModel):
    job_id: str
    source_url: str
    platform: str | None
    status: JobStatus
    stage: str | None
    progress: int
    error_message: str | None
    created_at: datetime | None
    updated_at: datetime | None
    completed_at: datetime | None


class JobListResponse(BaseModel):
    items: list[JobListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class JobLogItem(BaseModel):
    id: str
    level: str
    stage: str | None
    message: str
    data: dict | None
    created_at: datetime | None
