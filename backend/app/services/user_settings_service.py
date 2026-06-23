from app.models import User
from app.schemas.settings import UserSettingsPayload


class UserSettingsService:
    @staticmethod
    def default_settings() -> UserSettingsPayload:
        return UserSettingsPayload()

    @staticmethod
    def get_user_settings(user: User) -> UserSettingsPayload:
        raw = user.settings_json if isinstance(user.settings_json, dict) else {}
        return UserSettingsPayload.model_validate({**UserSettingsService.default_settings().model_dump(), **raw})

    @staticmethod
    def set_user_settings(user: User, payload: UserSettingsPayload) -> None:
        user.settings_json = payload.model_dump()

    @staticmethod
    def build_job_render_defaults(
        *,
        burn_subtitle: bool,
        mix_original_audio: bool,
        settings_payload: UserSettingsPayload,
    ) -> dict:
        return {
            "trim_start_seconds": 0.0,
            "trim_end_seconds": None,
            "playback_speed": 1.0,
            "blur_original_subtitles": False,
            "blur_x_ratio": 0.0,
            "blur_y_ratio": 0.78,
            "blur_width_ratio": 1.0,
            "blur_height_ratio": 0.22,
            "blur_strength": 11,
            "blur_masks": [],
            "voice_volume_percent": settings_payload.default_voice_volume_percent,
            "original_volume_percent": (
                settings_payload.default_original_volume_percent if mix_original_audio else 0
            ),
            "burn_audio": True,
            "burn_original_audio": mix_original_audio,
            "burn_subtitle": bool(burn_subtitle),
            "subtitle_font_size": settings_payload.default_subtitle_font_size,
            "subtitle_position": settings_payload.default_subtitle_position,
            "subtitle_text_color": settings_payload.default_subtitle_text_color,
            "subtitle_segments": None,
            "overlay_enabled": False,
            "overlay_text": "",
            "overlay_position": "top_right",
            "overlay_x_ratio": 0.0,
            "overlay_y_ratio": 0.0,
            "overlay_font_size": 18,
            "overlay_text_color": "#FFFFFF",
            "overlays": [],
        }
