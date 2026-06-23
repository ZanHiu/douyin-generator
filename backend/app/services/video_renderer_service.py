import subprocess
from pathlib import Path
from typing import Literal

from app.core.config import settings
from app.services.errors import ProcessingError
from app.services.storage_service import StorageService


class VideoRendererService:
    def __init__(self, storage: StorageService | None = None) -> None:
        self.storage = storage or StorageService()

    def render(
        self,
        job_id: str,
        input_video_path: str,
        tts_audio_path: str,
        subtitle_path: str,
        original_audio_path: str | None = None,
        mix_original_audio: bool = False,
        burn_subtitle: bool = True,
        output_filename: str = "output_vi.mp4",
        blur_original_subtitles: bool = False,
        blur_x_ratio: float = 0.0,
        blur_y_ratio: float = 0.78,
        blur_width_ratio: float = 1.0,
        blur_height_ratio: float = 0.22,
        blur_strength: int = 11,
        subtitle_font_size: int = 18,
        subtitle_position: Literal["bottom", "lower_third", "top"] = "bottom",
        subtitle_text_color: str = "#FFFFFF",
    ) -> str:
        input_path = self._require_file(input_video_path, "Missing input video.", resolve_storage=True)
        voice_path = self._require_file(tts_audio_path, "Missing Vietnamese voice audio.", resolve_storage=True)
        subtitles_path = (
            self._require_file(subtitle_path, "Missing subtitle file.", resolve_storage=True) if burn_subtitle else None
        )
        original_audio = (
            self._require_file(original_audio_path, "Missing original audio for final mix.", resolve_storage=True)
            if mix_original_audio
            else None
        )
        output_path = self.storage.job_dir(job_id) / output_filename
        video_duration = self._probe_duration_seconds(input_path)
        render_voice_path = self.storage.job_dir(job_id) / "voice_vi_render.wav"
        self._prepare_voice_for_render(voice_path, render_voice_path, video_duration)

        args = self._build_render_args(
            input_path,
            render_voice_path,
            subtitles_path,
            output_path,
            original_audio_path=original_audio,
            burn_subtitle=burn_subtitle,
            blur_original_subtitles=blur_original_subtitles,
            blur_x_ratio=blur_x_ratio,
            blur_y_ratio=blur_y_ratio,
            blur_width_ratio=blur_width_ratio,
            blur_height_ratio=blur_height_ratio,
            blur_strength=blur_strength,
            subtitle_font_size=subtitle_font_size,
            subtitle_position=subtitle_position,
            subtitle_text_color=subtitle_text_color,
        )

        try:
            subprocess.run(
                args,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as exc:
            raise ProcessingError(
                "MISSING_BINARY",
                f"Missing tool: {settings.ffmpeg_bin}. Check PATH or FFMPEG_BIN.",
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            message = f"Could not render video with FFmpeg. {detail}" if detail else "Could not render video with FFmpeg."
            raise ProcessingError("RENDER_FAILED", message) from exc

        if not output_path.exists():
            raise ProcessingError("RENDER_FAILED", f"FFmpeg did not create {output_filename}.")
        self._assert_output_has_audio(output_path)

        return str(output_path)

    def render_edit(
        self,
        job_id: str,
        edit_id: str,
        input_video_path: str,
        tts_audio_path: str | None,
        subtitle_path: str | None,
        *,
        original_audio_path: str | None = None,
        output_filename: str = "output_vi_edit.mp4",
        trim_start_seconds: float = 0.0,
        trim_end_seconds: float | None = None,
        playback_speed: float = 1.0,
        blur_original_subtitles: bool = False,
        blur_x_ratio: float = 0.0,
        blur_y_ratio: float = 0.78,
        blur_width_ratio: float = 1.0,
        blur_height_ratio: float = 0.22,
        blur_strength: int = 11,
        blur_masks: list[dict] | None = None,
        voice_volume_percent: int = 100,
        original_volume_percent: int = 35,
        burn_audio: bool = True,
        burn_original_audio: bool = True,
        burn_subtitle: bool = True,
        subtitle_font_size: int = 18,
        subtitle_position: Literal["bottom", "lower_third", "top"] = "bottom",
        subtitle_text_color: str = "#FFFFFF",
        overlay_enabled: bool = False,
        overlay_text: str = "",
        overlay_position: Literal[
            "top_left",
            "top_center",
            "top_right",
            "bottom_left",
            "bottom_center",
            "bottom_right",
            "custom",
        ] = "top_right",
        overlay_x_ratio: float = 0.0,
        overlay_y_ratio: float = 0.0,
        overlay_font_size: int = 18,
        overlay_text_color: str = "#FFFFFF",
        overlays: list[dict] | None = None,
    ) -> str:
        input_path = self._require_file(input_video_path, "Missing input video.", resolve_storage=True)
        subtitle_file = (
            self._require_file(subtitle_path, "Missing subtitle file.", resolve_storage=True) if burn_subtitle else None
        )
        original_audio = (
            self._require_file(original_audio_path, "Missing original audio for edit render.", resolve_storage=True)
            if original_audio_path and original_volume_percent > 0 and burn_original_audio
            else None
        )

        if trim_end_seconds is not None and trim_end_seconds <= trim_start_seconds:
            raise ProcessingError("RENDER_FAILED", "Trim end must be greater than trim start.")

        edit_dir = self.storage.edit_dir(job_id, edit_id)

        voice_input: Path | None = None
        if tts_audio_path and burn_audio and voice_volume_percent > 0:
            voice_path = self._require_file(tts_audio_path, "Missing Vietnamese voice audio.", resolve_storage=True)
            voice_input = edit_dir / "voice_vi_render.wav"
            video_duration = self._probe_duration_seconds(input_path)
            self._prepare_voice_for_render(voice_path, voice_input, video_duration)

        output_path = edit_dir / output_filename
        include_audio = voice_input is not None or original_audio is not None
        args = self._build_edit_render_args(
            input_path=input_path,
            voice_path=voice_input,
            original_audio_path=original_audio,
            subtitle_path=subtitle_file,
            output_path=output_path,
            trim_start_seconds=trim_start_seconds,
            trim_end_seconds=trim_end_seconds,
            playback_speed=playback_speed,
            blur_original_subtitles=blur_original_subtitles,
            blur_x_ratio=blur_x_ratio,
            blur_y_ratio=blur_y_ratio,
            blur_width_ratio=blur_width_ratio,
            blur_height_ratio=blur_height_ratio,
            blur_strength=blur_strength,
            blur_masks=blur_masks,
            voice_volume_multiplier=max(voice_volume_percent, 0) / 100,
            original_volume_multiplier=max(original_volume_percent, 0) / 100,
            include_audio=include_audio,
            burn_subtitle=burn_subtitle,
            subtitle_font_size=subtitle_font_size,
            subtitle_position=subtitle_position,
            subtitle_text_color=subtitle_text_color,
            overlay_enabled=overlay_enabled,
            overlay_text=overlay_text,
            overlay_position=overlay_position,
            overlay_x_ratio=overlay_x_ratio,
            overlay_y_ratio=overlay_y_ratio,
            overlay_font_size=overlay_font_size,
            overlay_text_color=overlay_text_color,
            overlays=overlays,
        )

        try:
            subprocess.run(
                args,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as exc:
            raise ProcessingError(
                "MISSING_BINARY",
                f"Missing tool: {settings.ffmpeg_bin}. Check PATH or FFMPEG_BIN.",
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            message = f"Could not render edited video with FFmpeg. {detail}" if detail else "Could not render edited video with FFmpeg."
            raise ProcessingError("RENDER_FAILED", message) from exc

        if not output_path.exists():
            raise ProcessingError("RENDER_FAILED", f"FFmpeg did not create {output_filename}.")
        if include_audio:
            self._assert_output_has_audio(output_path)

        return str(output_path)

    def _prepare_voice_for_render(self, voice_path: Path, output_path: Path, duration_seconds: float) -> None:
        args = self._build_voice_polish_args(voice_path, output_path, duration_seconds)
        try:
            subprocess.run(
                args,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as exc:
            raise ProcessingError(
                "MISSING_BINARY",
                f"Missing tool: {settings.ffmpeg_bin}. Check PATH or FFMPEG_BIN.",
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            message = (
                f"Could not prepare Vietnamese voice audio with FFmpeg. {detail}"
                if detail
                else "Could not prepare Vietnamese voice audio with FFmpeg."
            )
            raise ProcessingError("RENDER_FAILED", message) from exc

        if not output_path.exists():
            raise ProcessingError("RENDER_FAILED", "FFmpeg did not create voice_vi_render.wav.")

    def _probe_duration_seconds(self, input_path: Path) -> float:
        args = [
            settings.ffprobe_bin,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(input_path),
        ]
        try:
            result = subprocess.run(
                args,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as exc:
            raise ProcessingError(
                "MISSING_BINARY",
                f"Missing tool: {settings.ffprobe_bin}. Check PATH or FFPROBE_BIN.",
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            message = (
                f"Could not read video duration with FFprobe. {detail}"
                if detail
                else "Could not read video duration with FFprobe."
            )
            raise ProcessingError("RENDER_FAILED", message) from exc

        try:
            duration = float(result.stdout.strip())
        except ValueError as exc:
            raise ProcessingError("RENDER_FAILED", f"Invalid video duration: {result.stdout.strip()}") from exc

        if duration <= 0:
            raise ProcessingError("RENDER_FAILED", "Video duration must be greater than 0.")
        return duration

    def _assert_output_has_audio(self, output_path: Path) -> None:
        args = [
            settings.ffprobe_bin,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_type,codec_name",
            "-of",
            "default=noprint_wrappers=1",
            str(output_path),
        ]
        try:
            result = subprocess.run(
                args,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as exc:
            raise ProcessingError(
                "MISSING_BINARY",
                f"Missing tool: {settings.ffprobe_bin}. Check PATH or FFPROBE_BIN.",
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            message = (
                f"Could not verify output audio with FFprobe. {detail}"
                if detail
                else "Could not verify output audio with FFprobe."
            )
            raise ProcessingError("RENDER_FAILED", message) from exc

        if "codec_type=audio" not in result.stdout:
            raise ProcessingError("RENDER_FAILED", "Final video has no Vietnamese audio stream.")

    @staticmethod
    def _build_render_args(
        input_path: Path,
        render_voice_path: Path,
        subtitles_path: Path | None,
        output_path: Path,
        original_audio_path: Path | None = None,
        burn_subtitle: bool = True,
        blur_original_subtitles: bool = False,
        blur_x_ratio: float = 0.0,
        blur_y_ratio: float = 0.78,
        blur_width_ratio: float = 1.0,
        blur_height_ratio: float = 0.22,
        blur_strength: int = 11,
        subtitle_font_size: int = 18,
        subtitle_position: Literal["bottom", "lower_third", "top"] = "bottom",
        subtitle_text_color: str = "#FFFFFF",
    ) -> list[str]:
        args = [
            settings.ffmpeg_bin,
            "-y",
            "-i",
            str(input_path),
            "-i",
            str(render_voice_path),
        ]
        if original_audio_path is not None:
            args.extend(["-i", str(original_audio_path)])

        video_filter = VideoRendererService._build_video_filter(
            subtitles_path,
            burn_subtitle=burn_subtitle,
            blur_original_subtitles=blur_original_subtitles,
            blur_x_ratio=blur_x_ratio,
            blur_y_ratio=blur_y_ratio,
            blur_width_ratio=blur_width_ratio,
            blur_height_ratio=blur_height_ratio,
            blur_strength=blur_strength,
            subtitle_font_size=subtitle_font_size,
            subtitle_position=subtitle_position,
            subtitle_text_color=subtitle_text_color,
        )

        if blur_original_subtitles:
            filter_parts = [video_filter]
            if original_audio_path is not None:
                filter_parts.append(VideoRendererService._build_audio_mix_filter())
            args.extend(["-filter_complex", ";".join(filter_parts), "-map", "[vout]"])
        elif video_filter:
            args.extend(["-vf", video_filter, "-map", "0:v:0"])
        else:
            args.extend(["-map", "0:v:0"])

        if original_audio_path is None:
            args.extend(["-map", "1:a:0"])
        else:
            if not blur_original_subtitles:
                args.extend(["-filter_complex", VideoRendererService._build_audio_mix_filter()])
            args.extend(["-map", "[aout]"])

        args.extend(
            [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-metadata:s:a:0",
            "language=vie",
            "-disposition:a:0",
            "default",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output_path),
            ]
        )
        return args

    def _require_file(self, path_value: str | None, message: str, *, resolve_storage: bool = False) -> Path:
        if not path_value:
            raise ProcessingError("RENDER_FAILED", message)
        path = self.storage.resolve_path(path_value) if resolve_storage else Path(path_value)
        if not path.exists():
            raise ProcessingError("RENDER_FAILED", message)
        return path

    @staticmethod
    def _build_audio_mix_filter() -> str:
        return (
            f"[1:a]volume={settings.mixed_voice_volume_multiplier}[voice];"
            f"[2:a]volume={settings.original_audio_volume_multiplier}[original];"
            "[voice][original]amix=inputs=2:duration=first:dropout_transition=0[aout]"
        )

    @staticmethod
    def _build_video_filter(
        subtitles_path: Path | None,
        *,
        burn_subtitle: bool,
        blur_original_subtitles: bool,
        blur_x_ratio: float,
        blur_y_ratio: float,
        blur_width_ratio: float,
        blur_height_ratio: float,
        blur_strength: int,
        subtitle_font_size: int,
        subtitle_position: Literal["bottom", "lower_third", "top"],
        subtitle_text_color: str,
    ) -> str | None:
        subtitle_filter = (
            VideoRendererService._build_subtitle_filter(
                subtitles_path,
                subtitle_font_size,
                subtitle_position,
                subtitle_text_color,
            )
            if burn_subtitle and subtitles_path is not None
            else None
        )
        if not blur_original_subtitles:
            if subtitle_filter is None:
                return None
            return subtitle_filter

        x_ratio = min(max(blur_x_ratio, 0.0), 0.95)
        y_ratio = min(max(blur_y_ratio, 0.0), 0.95)
        width_ratio = min(max(blur_width_ratio, 0.05), 1.0)
        height_ratio = min(max(blur_height_ratio, 0.05), 0.45)
        if x_ratio + width_ratio > 1.0:
            width_ratio = max(0.05, 1.0 - x_ratio)
        if y_ratio + height_ratio > 1.0:
            height_ratio = max(0.05, 1.0 - y_ratio)
        strength = min(max(blur_strength, 2), 40)
        if subtitle_filter is None:
            raise ProcessingError("RENDER_FAILED", "Blur rendering requires burned subtitles in the video filter.")
        return (
            f"[0:v]split[base][blur];"
            f"[blur]crop=iw*{width_ratio:.4f}:ih*{height_ratio:.4f}:iw*{x_ratio:.4f}:ih*{y_ratio:.4f},"
            f"boxblur=luma_radius={strength}:luma_power=1[blurred];"
            f"[base][blurred]overlay=W*{x_ratio:.4f}:H*{y_ratio:.4f},{subtitle_filter}[vout]"
        )

    @staticmethod
    def _build_voice_polish_args(voice_path: Path, output_path: Path, duration_seconds: float) -> list[str]:
        duration = max(duration_seconds, 0.1)
        audio_filter = (
            f"volume={settings.voice_volume_multiplier},"
            f"loudnorm=I={settings.voice_loudnorm_target_i}:"
            f"TP={settings.voice_loudnorm_target_tp}:"
            f"LRA={settings.voice_loudnorm_target_lra},"
            f"apad,"
            f"atrim=0:{duration:.3f},"
            "asetpts=N/SR/TB"
        )
        return [
            settings.ffmpeg_bin,
            "-y",
            "-i",
            str(voice_path),
            "-af",
            audio_filter,
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(settings.tts_sample_rate),
            "-ac",
            "1",
            str(output_path),
        ]

    @staticmethod
    def _escape_subtitle_filter_path(path: Path) -> str:
        # FFmpeg subtitles filter treats ':' and '\' specially on Windows.
        normalized = path.resolve().as_posix()
        return normalized.replace(":", "\\:").replace("'", "\\'")

    @staticmethod
    def _build_edit_render_args(
        *,
        input_path: Path,
        voice_path: Path | None,
        original_audio_path: Path | None,
        subtitle_path: Path | None,
        output_path: Path,
        trim_start_seconds: float = 0.0,
        trim_end_seconds: float | None = None,
        playback_speed: float = 1.0,
        blur_original_subtitles: bool = False,
        blur_x_ratio: float = 0.0,
        blur_y_ratio: float = 0.78,
        blur_width_ratio: float = 1.0,
        blur_height_ratio: float = 0.22,
        blur_strength: int = 11,
        blur_masks: list[dict] | None = None,
        voice_volume_multiplier: float = 1.0,
        original_volume_multiplier: float = 0.35,
        include_audio: bool = True,
        burn_subtitle: bool = True,
        subtitle_font_size: int = 18,
        subtitle_position: Literal["bottom", "lower_third", "top"] = "bottom",
        subtitle_text_color: str = "#FFFFFF",
        overlay_enabled: bool = False,
        overlay_text: str = "",
        overlay_position: Literal[
            "top_left",
            "top_center",
            "top_right",
            "bottom_left",
            "bottom_center",
            "bottom_right",
            "custom",
        ] = "top_right",
        overlay_x_ratio: float = 0.0,
        overlay_y_ratio: float = 0.0,
        overlay_font_size: int = 18,
        overlay_text_color: str = "#FFFFFF",
        overlays: list[dict] | None = None,
    ) -> list[str]:
        args = [settings.ffmpeg_bin, "-y", "-i", str(input_path)]
        voice_index: int | None = None
        original_index: int | None = None

        if voice_path is not None:
            voice_index = len([part for part in args if part == "-i"])
            args.extend(["-i", str(voice_path)])
        if original_audio_path is not None:
            original_index = len([part for part in args if part == "-i"])
            args.extend(["-i", str(original_audio_path)])

        filters = [
            VideoRendererService._build_edit_video_filter(
                subtitle_path=subtitle_path,
                trim_start_seconds=trim_start_seconds,
                trim_end_seconds=trim_end_seconds,
                playback_speed=playback_speed,
                blur_original_subtitles=blur_original_subtitles,
                blur_x_ratio=blur_x_ratio,
                blur_y_ratio=blur_y_ratio,
                blur_width_ratio=blur_width_ratio,
                blur_height_ratio=blur_height_ratio,
                blur_strength=blur_strength,
                blur_masks=blur_masks,
                burn_subtitle=burn_subtitle,
                subtitle_font_size=subtitle_font_size,
                subtitle_position=subtitle_position,
                subtitle_text_color=subtitle_text_color,
                overlay_enabled=overlay_enabled,
                overlay_text=overlay_text,
                overlay_position=overlay_position,
                overlay_x_ratio=overlay_x_ratio,
                overlay_y_ratio=overlay_y_ratio,
                overlay_font_size=overlay_font_size,
                overlay_text_color=overlay_text_color,
                overlays=overlays,
            )
        ]

        audio_output_label = VideoRendererService._build_edit_audio_filter(
            filters=filters,
            voice_index=voice_index,
            original_index=original_index,
            trim_start_seconds=trim_start_seconds,
            trim_end_seconds=trim_end_seconds,
            playback_speed=playback_speed,
            voice_volume_multiplier=voice_volume_multiplier,
            original_volume_multiplier=original_volume_multiplier,
            include_audio=include_audio,
        )

        args.extend(["-filter_complex", ";".join(filters), "-map", "[vout]"])
        if audio_output_label:
            args.extend(["-map", audio_output_label])
        else:
            args.append("-an")

        args.extend(["-c:v", "libx264", "-preset", "veryfast"])
        if audio_output_label:
            args.extend(
                [
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-ar",
                    "44100",
                    "-ac",
                    "2",
                    "-metadata:s:a:0",
                    "language=vie",
                    "-disposition:a:0",
                    "default",
                ]
            )
        args.extend(["-movflags", "+faststart", "-shortest", str(output_path)])
        return args

    @staticmethod
    def _build_edit_video_filter(
        *,
        subtitle_path: Path | None,
        trim_start_seconds: float,
        trim_end_seconds: float | None,
        playback_speed: float,
        blur_original_subtitles: bool,
        blur_x_ratio: float,
        blur_y_ratio: float,
        blur_width_ratio: float,
        blur_height_ratio: float,
        blur_strength: int,
        blur_masks: list[dict] | None,
        burn_subtitle: bool,
        subtitle_font_size: int,
        subtitle_position: Literal["bottom", "lower_third", "top"],
        subtitle_text_color: str,
        overlay_enabled: bool,
        overlay_text: str,
        overlay_position: Literal[
            "top_left",
            "top_center",
            "top_right",
            "bottom_left",
            "bottom_center",
            "bottom_right",
            "custom",
        ],
        overlay_x_ratio: float,
        overlay_y_ratio: float,
        overlay_font_size: int,
        overlay_text_color: str,
        overlays: list[dict] | None,
    ) -> str:
        segments: list[str] = []
        video_filters = VideoRendererService._build_video_transform_steps(
            trim_start_seconds=trim_start_seconds,
            trim_end_seconds=trim_end_seconds,
            playback_speed=playback_speed,
        )
        if video_filters:
            segments.append(f"[0:v]{','.join(video_filters)}[vbase]")
        else:
            segments.append("[0:v]null[vbase]")

        current_label = "[vbase]"
        normalized_blur_masks = blur_masks or []
        if not normalized_blur_masks and blur_original_subtitles:
            normalized_blur_masks = [
                {
                    "x_ratio": blur_x_ratio,
                    "y_ratio": blur_y_ratio,
                    "width_ratio": blur_width_ratio,
                    "height_ratio": blur_height_ratio,
                    "strength": blur_strength,
                }
            ]
        for index, blur_mask in enumerate(normalized_blur_masks):
            x_ratio, y_ratio, width_ratio, height_ratio, strength = VideoRendererService._normalize_blur_mask(blur_mask)
            clean_label = f"[vclean{index}]"
            blur_label = f"[vblur{index}]"
            blurred_label = f"[vblurred{index}]"
            post_label = f"[vpost{index}]"
            segments.append(f"{current_label}split{clean_label}{blur_label}")
            segments.append(
                f"{blur_label}crop=iw*{width_ratio:.4f}:ih*{height_ratio:.4f}:iw*{x_ratio:.4f}:ih*{y_ratio:.4f},"
                f"boxblur=luma_radius={strength}:luma_power=1{blurred_label}"
            )
            segments.append(f"{clean_label}{blurred_label}overlay=W*{x_ratio:.4f}:H*{y_ratio:.4f}{post_label}")
            current_label = post_label

        if burn_subtitle and subtitle_path is not None:
            segments.append(
                f"{current_label}{VideoRendererService._build_subtitle_filter(subtitle_path, subtitle_font_size, subtitle_position, subtitle_text_color)}[vout]"
            )
        else:
            segments.append(f"{current_label}null[vout]")

        normalized_overlays = overlays or []
        if not normalized_overlays and overlay_enabled and overlay_text.strip():
            normalized_overlays = [
                {
                    "text": overlay_text,
                    "position": overlay_position,
                    "x_ratio": overlay_x_ratio,
                    "y_ratio": overlay_y_ratio,
                    "font_size": overlay_font_size,
                    "text_color": overlay_text_color,
                }
            ]
        current_overlay_label = "[vout]"
        for index, overlay in enumerate(normalized_overlays):
            overlay_label = f"[voverlay{index}]"
            segments.append(
                f"{current_overlay_label}{VideoRendererService._build_overlay_filter_from_item(overlay)}{overlay_label}"
            )
            current_overlay_label = overlay_label
        if current_overlay_label != "[vout]":
            segments.append(f"{current_overlay_label}null[vout]")
        return ";".join(segments)

    @staticmethod
    def _build_edit_audio_filter(
        *,
        filters: list[str],
        voice_index: int | None,
        original_index: int | None,
        trim_start_seconds: float,
        trim_end_seconds: float | None,
        playback_speed: float,
        voice_volume_multiplier: float,
        original_volume_multiplier: float,
        include_audio: bool,
    ) -> str | None:
        if not include_audio:
            return None

        inputs: list[str] = []
        if voice_index is not None and voice_volume_multiplier > 0:
            filters.append(
                f"[{voice_index}:a]{','.join(VideoRendererService._build_audio_transform_steps(trim_start_seconds, trim_end_seconds, playback_speed, voice_volume_multiplier))}[voice]"
            )
            inputs.append("[voice]")
        if original_index is not None and original_volume_multiplier > 0:
            filters.append(
                f"[{original_index}:a]{','.join(VideoRendererService._build_audio_transform_steps(trim_start_seconds, trim_end_seconds, playback_speed, original_volume_multiplier))}[original]"
            )
            inputs.append("[original]")

        if not inputs:
            return None
        if len(inputs) == 1:
            filters.append(f"{inputs[0]}anull[aout]")
            return "[aout]"

        filters.append(f"{''.join(inputs)}amix=inputs={len(inputs)}:duration=longest:dropout_transition=0[aout]")
        return "[aout]"

    @staticmethod
    def _build_video_transform_steps(
        *,
        trim_start_seconds: float,
        trim_end_seconds: float | None,
        playback_speed: float,
    ) -> list[str]:
        steps = [VideoRendererService._build_trim_step(trim_start_seconds, trim_end_seconds, audio=False), "setpts=PTS-STARTPTS"]
        if abs(playback_speed - 1.0) > 0.0001:
            steps.append(f"setpts=PTS/{playback_speed:.4f}")
        return steps

    @staticmethod
    def _build_audio_transform_steps(
        trim_start_seconds: float,
        trim_end_seconds: float | None,
        playback_speed: float,
        volume_multiplier: float,
    ) -> list[str]:
        steps = [
            VideoRendererService._build_trim_step(trim_start_seconds, trim_end_seconds, audio=True),
            "asetpts=PTS-STARTPTS",
        ]
        if abs(playback_speed - 1.0) > 0.0001:
            steps.append(f"atempo={playback_speed:.4f}")
        steps.append(f"volume={volume_multiplier:.4f}")
        return steps

    @staticmethod
    def _build_trim_step(trim_start_seconds: float, trim_end_seconds: float | None, *, audio: bool) -> str:
        filter_name = "atrim" if audio else "trim"
        if trim_end_seconds is None:
            return f"{filter_name}=start={trim_start_seconds:.3f}"
        return f"{filter_name}=start={trim_start_seconds:.3f}:end={trim_end_seconds:.3f}"

    @staticmethod
    def _build_subtitle_filter(
        subtitle_path: Path,
        subtitle_font_size: int,
        subtitle_position: Literal["bottom", "lower_third", "top"],
        subtitle_text_color: str,
    ) -> str:
        style = VideoRendererService._build_subtitle_style(
            subtitle_font_size=subtitle_font_size,
            subtitle_position=subtitle_position,
            subtitle_text_color=subtitle_text_color,
        )
        return (
            f"subtitles='{VideoRendererService._escape_subtitle_filter_path(subtitle_path)}'"
            f":force_style='{style}'"
        )

    @staticmethod
    def _build_subtitle_style(
        *,
        subtitle_font_size: int,
        subtitle_position: Literal["bottom", "lower_third", "top"],
        subtitle_text_color: str,
    ) -> str:
        alignment = "2"
        margin_v = "36"
        if subtitle_position == "lower_third":
            margin_v = "120"
        elif subtitle_position == "top":
            alignment = "8"

        return (
            f"Fontsize={subtitle_font_size},"
            f"Alignment={alignment},"
            f"MarginV={margin_v},"
            f"PrimaryColour={VideoRendererService._hex_to_ass_color(subtitle_text_color)},"
            "OutlineColour=&H00000000,"
            "BorderStyle=1,"
            "Outline=2,"
            "Shadow=0"
        )

    @staticmethod
    def _build_overlay_filter(
        overlay_text: str,
        overlay_position: Literal[
            "top_left",
            "top_center",
            "top_right",
            "bottom_left",
            "bottom_center",
            "bottom_right",
            "custom",
        ],
        overlay_x_ratio: float,
        overlay_y_ratio: float,
        overlay_font_size: int,
        overlay_text_color: str,
    ) -> str:
        x_expr, y_expr = VideoRendererService._overlay_position_xy(
            overlay_position,
            overlay_x_ratio,
            overlay_y_ratio,
        )
        x_expr = VideoRendererService._escape_drawtext_expr(x_expr)
        y_expr = VideoRendererService._escape_drawtext_expr(y_expr)
        escaped_text = VideoRendererService._escape_drawtext_text(overlay_text)
        return (
            "drawtext="
            f"text='{escaped_text}':"
            f"x={x_expr}:"
            f"y={y_expr}:"
            f"fontsize={overlay_font_size}:"
            f"fontcolor={overlay_text_color}:"
            "borderw=2:"
            "bordercolor=black:"
            "shadowx=0:"
            "shadowy=0"
        )

    @staticmethod
    def _build_overlay_filter_from_item(overlay: dict) -> str:
        return VideoRendererService._build_overlay_filter(
            str(overlay.get("text", "")).strip(),
            overlay.get("position", "top_right"),
            float(overlay.get("x_ratio", 0.0)),
            float(overlay.get("y_ratio", 0.0)),
            int(overlay.get("font_size", 18)),
            str(overlay.get("text_color", "#FFFFFF")),
        )

    @staticmethod
    def _normalize_blur_mask(blur_mask: dict) -> tuple[float, float, float, float, int]:
        x_ratio = min(max(float(blur_mask.get("x_ratio", 0.0)), 0.0), 0.95)
        y_ratio = min(max(float(blur_mask.get("y_ratio", 0.78)), 0.0), 0.95)
        width_ratio = min(max(float(blur_mask.get("width_ratio", 1.0)), 0.05), 1.0)
        height_ratio = min(max(float(blur_mask.get("height_ratio", 0.22)), 0.05), 0.45)
        if x_ratio + width_ratio > 1.0:
            width_ratio = max(0.05, 1.0 - x_ratio)
        if y_ratio + height_ratio > 1.0:
            height_ratio = max(0.05, 1.0 - y_ratio)
        strength = min(max(int(blur_mask.get("strength", 11)), 2), 11)
        return x_ratio, y_ratio, width_ratio, height_ratio, strength

    @staticmethod
    def _overlay_position_xy(
        overlay_position: Literal[
            "top_left",
            "top_center",
            "top_right",
            "bottom_left",
            "bottom_center",
            "bottom_right",
            "custom",
        ],
        overlay_x_ratio: float,
        overlay_y_ratio: float,
    ) -> tuple[str, str]:
        if overlay_position == "custom":
            x_ratio = min(max(overlay_x_ratio, 0.0), 1.0)
            y_ratio = min(max(overlay_y_ratio, 0.0), 1.0)
            return (
                f"max(0,min(w-text_w,w*{x_ratio:.4f}))",
                f"max(0,min(h-text_h,h*{y_ratio:.4f}))",
            )
        positions = {
            "top_left": ("36", "36"),
            "top_center": ("(w-text_w)/2", "36"),
            "top_right": ("w-text_w-36", "36"),
            "bottom_left": ("36", "h-text_h-96"),
            "bottom_center": ("(w-text_w)/2", "h-text_h-96"),
            "bottom_right": ("w-text_w-36", "h-text_h-96"),
        }
        return positions[overlay_position]

    @staticmethod
    def _escape_drawtext_text(value: str) -> str:
        return (
            value.replace("\\", "\\\\")
            .replace(":", "\\:")
            .replace("'", "\\'")
            .replace("%", "\\%")
            .replace(",", "\\,")
            .replace("[", "\\[")
            .replace("]", "\\]")
        )

    @staticmethod
    def _escape_drawtext_expr(value: str) -> str:
        return value.replace("\\", "\\\\").replace(",", "\\,")

    @staticmethod
    def _hex_to_ass_color(value: str) -> str:
        normalized = value.strip().lstrip("#")
        red = normalized[0:2]
        green = normalized[2:4]
        blue = normalized[4:6]
        return f"&H00{blue}{green}{red}"
