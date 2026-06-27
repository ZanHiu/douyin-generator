from __future__ import annotations

from copy import deepcopy
from typing import Literal
from uuid import uuid4

from app.schemas.job import BlurMaskItem, JobEditRenderRequest, JobSubtitleSegment, OverlayItem
from app.services.errors import ProcessingError
from app.services.job_service import JobService
from app.services.subtitle_service import SubtitleService
from app.services.video_renderer_service import VideoRendererService

EDIT_RENDER_STATUS_KEY = "_render_status"
EDIT_RENDER_ERROR_KEY = "_render_error_message"
EDIT_RENDER_TASK_ID_KEY = "_render_task_id"

EditRenderStatus = Literal["queued", "processing", "completed", "failed"]


def get_edit_render_status(config: dict | None) -> EditRenderStatus:
    value = (config or {}).get(EDIT_RENDER_STATUS_KEY)
    if value in {"queued", "processing", "completed", "failed"}:
        return value
    return "completed"


def get_edit_render_error(config: dict | None) -> str | None:
    value = (config or {}).get(EDIT_RENDER_ERROR_KEY)
    return str(value) if value else None


def strip_edit_runtime_metadata(config: dict | None) -> dict:
    normalized = deepcopy(config or {})
    normalized.pop(EDIT_RENDER_STATUS_KEY, None)
    normalized.pop(EDIT_RENDER_ERROR_KEY, None)
    normalized.pop(EDIT_RENDER_TASK_ID_KEY, None)
    return normalized


def set_edit_render_metadata(
    config: dict,
    *,
    status: EditRenderStatus,
    error_message: str | None = None,
    task_id: str | None = None,
) -> dict:
    normalized = strip_edit_runtime_metadata(config)
    normalized[EDIT_RENDER_STATUS_KEY] = status
    normalized[EDIT_RENDER_ERROR_KEY] = error_message
    normalized[EDIT_RENDER_TASK_ID_KEY] = task_id
    return normalized


def prepare_edit_render_request(
    service: JobService,
    *,
    job_id: str,
    payload: JobEditRenderRequest,
    overwrite_edit_id: str | None,
) -> tuple[str, str]:
    job = service.get_job(job_id)
    if job is None:
        raise ProcessingError("UNKNOWN_ERROR", "Job not found")
    if job.status != "completed":
        raise ProcessingError("EDIT_NOT_READY", "Only completed jobs can be edited")
    if not job.input_video_path or not job.tts_audio_path or not job.subtitle_path:
        raise ProcessingError("EDIT_NOT_READY", "Required render artifacts are missing")

    edit_id = overwrite_edit_id or str(uuid4())
    config_json = _build_edit_config_payload(payload)
    pending_config = set_edit_render_metadata(config_json, status="queued")
    result_url = f"/api/jobs/{job_id}/edits/{edit_id}/download"
    tool_summary = _build_edit_tool_summary(
        payload,
        _load_original_segments(service, job),
        default_burn_original_audio=bool(job.mix_original_audio),
    )

    if overwrite_edit_id:
        existing_edit = service.get_edit(overwrite_edit_id)
        if existing_edit is None or existing_edit.job_id != job_id or existing_edit.is_draft:
            raise ProcessingError("UNKNOWN_ERROR", "Saved edit not found")
        service.update_edit_state(
            overwrite_edit_id,
            tool_summary=tool_summary,
            config_json=pending_config,
            result_url=result_url,
        )
    else:
        service.create_edit(
            job_id,
            edit_id=edit_id,
            tool_summary=tool_summary,
            config_json=pending_config,
            output_video_path=None,
            result_url=result_url,
            is_draft=True,
        )

    service.log(
        job_id,
        "info",
        "editing",
        "Queued edited video render",
        {
            "edit_id": edit_id,
            "overwrite_edit_id": overwrite_edit_id,
            "tool_summary": tool_summary,
        },
    )
    return edit_id, result_url


def run_edit_render(service: JobService, *, job_id: str, edit_id: str, task_id: str | None = None) -> str:
    job = service.get_job(job_id)
    edit = service.get_edit(edit_id)
    if job is None:
        raise ProcessingError("UNKNOWN_ERROR", "Job not found")
    if edit is None or edit.job_id != job_id:
        raise ProcessingError("UNKNOWN_ERROR", "Saved edit not found")
    if not job.input_video_path or not job.tts_audio_path or not job.subtitle_path:
        raise ProcessingError("EDIT_NOT_READY", "Required render artifacts are missing")

    clean_config = strip_edit_runtime_metadata(edit.config_json or {})
    payload = JobEditRenderRequest.model_validate(clean_config)
    processing_config = set_edit_render_metadata(clean_config, status="processing", task_id=task_id)
    service.update_edit_state(
        edit_id,
        tool_summary=edit.tool_summary,
        config_json=processing_config,
        result_url=f"/api/jobs/{job_id}/edits/{edit_id}/download",
    )
    service.log(job_id, "info", "editing", "Rendering edited video", {"edit_id": edit_id})

    input_video_path = str(service.storage.resolve_path(job.input_video_path))
    tts_audio_path = str(service.storage.resolve_path(job.tts_audio_path))
    subtitle_path = str(service.storage.resolve_path(job.subtitle_path))
    original_audio_path = str(service.storage.resolve_path(job.audio_path)) if job.audio_path else None
    transcript_vi_path = str(service.storage.resolve_path(job.transcript_vi_path)) if job.transcript_vi_path else None

    render_subtitle_path = subtitle_path
    if payload.subtitle_segments:
        edited_segments = [segment.model_dump() for segment in payload.subtitle_segments]
        subtitle_service = SubtitleService()
        subtitle_service.write_edit_segments_json(job_id, edit_id, "transcript_vi.json", edited_segments)
        render_subtitle_path = subtitle_service.write_edit_srt_from_segments(
            job_id,
            edit_id,
            "subtitles_vi.srt",
            edited_segments,
        )

    blur_masks = _normalize_blur_masks(payload)
    overlays = _normalize_overlays(payload)

    output_path = VideoRendererService().render_edit(
        job_id,
        edit_id,
        input_video_path,
        tts_audio_path,
        render_subtitle_path,
        original_audio_path=original_audio_path,
        output_filename="output_vi_edit.mp4",
        trim_start_seconds=payload.trim_start_seconds,
        trim_end_seconds=payload.trim_end_seconds,
        playback_speed=payload.playback_speed,
        blur_original_subtitles=payload.blur_original_subtitles,
        blur_x_ratio=payload.blur_x_ratio,
        blur_y_ratio=payload.blur_y_ratio,
        blur_width_ratio=payload.blur_width_ratio,
        blur_height_ratio=payload.blur_height_ratio,
        blur_strength=payload.blur_strength,
        blur_masks=[item.model_dump() for item in blur_masks],
        voice_volume_percent=payload.voice_volume_percent,
        original_volume_percent=payload.original_volume_percent,
        burn_audio=payload.burn_audio,
        burn_original_audio=payload.burn_original_audio,
        burn_subtitle=payload.burn_subtitle,
        subtitle_font_size=payload.subtitle_font_size,
        subtitle_position=payload.subtitle_position,
        subtitle_text_color=payload.subtitle_text_color,
        overlay_enabled=payload.overlay_enabled,
        overlay_text=payload.overlay_text,
        overlay_position=payload.overlay_position,
        overlay_x_ratio=payload.overlay_x_ratio,
        overlay_y_ratio=payload.overlay_y_ratio,
        overlay_font_size=payload.overlay_font_size,
        overlay_text_color=payload.overlay_text_color,
        overlays=[item.model_dump() for item in overlays],
    )

    completed_config = set_edit_render_metadata(clean_config, status="completed")
    result_url = f"/api/jobs/{job_id}/edits/{edit_id}/download"
    service.finalize_edit(
        edit_id,
        tool_summary=edit.tool_summary,
        config_json=completed_config,
        output_video_path=output_path,
        result_url=result_url,
    )
    service.log(
        job_id,
        "info",
        "editing",
        "Edited video rendered",
        {
            "edit_id": edit_id,
            "output_video_path": output_path,
        },
    )
    return output_path


def fail_edit_render(service: JobService, *, job_id: str, edit_id: str, error_message: str) -> None:
    edit = service.get_edit(edit_id)
    if edit is None or edit.job_id != job_id:
        return
    config = set_edit_render_metadata(
        strip_edit_runtime_metadata(edit.config_json or {}),
        status="failed",
        error_message=error_message,
    )
    service.update_edit_state(
        edit_id,
        tool_summary=edit.tool_summary,
        config_json=config,
        result_url=edit.result_url or f"/api/jobs/{job_id}/edits/{edit_id}/download",
    )
    service.log(job_id, "error", "editing", error_message, {"edit_id": edit_id})


def _build_edit_config_payload(payload: JobEditRenderRequest) -> dict:
    config_json = payload.model_dump()
    config_json["blur_masks"] = [item.model_dump() for item in _normalize_blur_masks(payload)]
    config_json["overlays"] = [item.model_dump() for item in _normalize_overlays(payload)]
    return config_json


def _load_original_segments(service: JobService, job) -> list[dict]:
    if not job.transcript_vi_path:
        return []
    transcript_vi_path = str(service.storage.resolve_path(job.transcript_vi_path))
    return SubtitleService().load_segments(transcript_vi_path)


def _normalize_blur_masks(payload: JobEditRenderRequest) -> list[BlurMaskItem]:
    if payload.blur_masks is not None:
        return [item for item in payload.blur_masks if item.enabled]

    if not payload.blur_original_subtitles:
        return []

    return [
        BlurMaskItem(
            id="blur-1",
            enabled=True,
            x_ratio=payload.blur_x_ratio,
            y_ratio=payload.blur_y_ratio,
            width_ratio=payload.blur_width_ratio,
            height_ratio=payload.blur_height_ratio,
            strength=payload.blur_strength,
        )
    ]


def _normalize_overlays(payload: JobEditRenderRequest) -> list[OverlayItem]:
    if payload.overlays is not None:
        return [item for item in payload.overlays if item.enabled and item.text]

    if not payload.overlay_enabled or not payload.overlay_text:
        return []

    return [
        OverlayItem(
            id="overlay-1",
            enabled=True,
            text=payload.overlay_text,
            position=payload.overlay_position,
            x_ratio=payload.overlay_x_ratio,
            y_ratio=payload.overlay_y_ratio,
            font_size=payload.overlay_font_size,
            text_color=payload.overlay_text_color,
        )
    ]


def _build_edit_tool_summary(
    payload: JobEditRenderRequest,
    original_segments: list[dict] | None = None,
    *,
    default_burn_original_audio: bool = True,
) -> str:
    groups: list[tuple[str, list[str]]] = []
    blur_masks = _normalize_blur_masks(payload)
    overlays = _normalize_overlays(payload)

    video_tools: list[str] = []
    if payload.trim_start_seconds > 0 or payload.trim_end_seconds is not None or abs(payload.playback_speed - 1.0) > 0.001:
        video_tools.append("Trim/Speed")
    if blur_masks:
        video_tools.append("Blur/Mask")
    if overlays:
        video_tools.append("Overlay")
    if video_tools:
        groups.append(("Video", list(dict.fromkeys(video_tools))))

    audio_tools: list[str] = []
    if payload.voice_volume_percent != 100:
        audio_tools.append("Voice volume")
    if payload.original_volume_percent != 35:
        audio_tools.append("Original volume")
    if payload.burn_audio is not True:
        audio_tools.append("Burn voice")
    if payload.burn_original_audio is not default_burn_original_audio:
        audio_tools.append("Burn original voice")
    if audio_tools:
        groups.append(("Audio", list(dict.fromkeys(audio_tools))))

    caption_tools: list[str] = []
    if payload.burn_subtitle is not True:
        caption_tools.append("Burn subtitle")
    if (
        payload.subtitle_font_size != 18
        or payload.subtitle_position != "bottom"
        or payload.subtitle_text_color != "#FFFFFF"
    ):
        caption_tools.append("Style/Position")
    if payload.subtitle_segments and original_segments:
        text_changed, timing_changed = _detect_subtitle_segment_changes(payload.subtitle_segments, original_segments)
        if text_changed:
            caption_tools.append("Caption editor")
        if timing_changed:
            caption_tools.append("Timing editor")
    if caption_tools:
        groups.append(("Captions", list(dict.fromkeys(caption_tools))))

    if not groups:
        return "Editor :: Preview render"

    group_label = " + ".join(label for label, _ in groups)
    options: list[str] = []
    for _, tools in groups:
        options.extend(tools)
    return f"{group_label} :: {' + '.join(dict.fromkeys(options))}"


def _detect_subtitle_segment_changes(
    edited_segments: list[JobSubtitleSegment],
    original_segments: list[dict],
) -> tuple[bool, bool]:
    original_by_id = {int(segment.get("id", index)): segment for index, segment in enumerate(original_segments)}
    text_changed = False
    timing_changed = False

    for segment in edited_segments:
        original = original_by_id.get(segment.id)
        if original is None:
            text_changed = True
            timing_changed = True
            continue
        if str(original.get("text_vi", "")).strip() != segment.text_vi.strip():
            text_changed = True
        if abs(float(original.get("start", 0.0)) - segment.start) > 0.0001:
            timing_changed = True
        if abs(float(original.get("end", 0.0)) - segment.end) > 0.0001:
            timing_changed = True

    return text_changed, timing_changed
