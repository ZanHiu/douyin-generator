from typing import Literal

from pydantic import BaseModel, Field, field_validator


SubtitlePosition = Literal["bottom", "lower_third", "top"]


class UserSettingsPayload(BaseModel):
    default_voice_id: str = Field(default="banmai", min_length=1, max_length=128)
    default_burn_subtitle: bool = True
    default_mix_original_audio: bool = False
    default_voice_volume_percent: int = Field(default=100, ge=0, le=200)
    default_original_volume_percent: int = Field(default=35, ge=0, le=200)
    default_subtitle_font_size: int = Field(default=18, ge=14, le=48)
    default_subtitle_position: SubtitlePosition = "bottom"
    default_subtitle_text_color: str = "#FFFFFF"

    @field_validator("default_subtitle_text_color")
    @classmethod
    def validate_hex_color(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 7 or not normalized.startswith("#"):
            raise ValueError("Color must be a hex color like #FFFFFF.")
        try:
            int(normalized[1:], 16)
        except ValueError as exc:
            raise ValueError("Color must be a valid hex color.") from exc
        return normalized


class UserSettingsResponse(BaseModel):
    settings: UserSettingsPayload
