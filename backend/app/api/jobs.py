from uuid import uuid4

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.dependencies import require_authenticated_user
from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.schemas.job import (
    BlurMaskItem,
    JobCreate,
    JobCreateResponse,
    JobEditorStateResponse,
    JobEditDetailResponse,
    JobEditListItem,
    JobEditListResponse,
    JobEditRenderRequest,
    JobEditRenderResponse,
    JobEditSort,
    JobEditToolFilter,
    JobListItem,
    JobListResponse,
    JobLogItem,
    JobSort,
    JobStatus,
    JobStatusResponse,
    JobSubtitleSegment,
    OverlayItem,
)
from app.services.job_service import JobService
from app.services.subtitle_service import SubtitleService
from app.services.user_settings_service import UserSettingsService
from app.services.video_renderer_service import VideoRendererService
from app.workers.celery_app import celery_app, recover_queue_state
from app.workers.tasks import process_job

router = APIRouter(dependencies=[Depends(require_authenticated_user)])


def _enqueue_job(service: JobService, job_id: str) -> None:
    recover_queue_state()
    task = process_job.delay(job_id)
    service.set_task_id(job_id, task.id)


def _resolve_stored_path(service: JobService, stored_path: str | None) -> str | None:
    if not stored_path:
        return None
    return str(service.storage.resolve_path(stored_path))


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


@router.post("", response_model=JobCreateResponse, status_code=201)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
) -> JobCreateResponse:
    service = JobService(db)
    user_settings = UserSettingsService.get_user_settings(user)
    job = service.create_job(
        payload,
        initial_render_config=UserSettingsService.build_job_render_defaults(
            burn_subtitle=payload.burn_subtitle,
            mix_original_audio=payload.mix_original_audio,
            settings_payload=user_settings,
        ),
    )
    _enqueue_job(service, job.id)
    return JobCreateResponse(job_id=job.id, status=job.status)


@router.post("/upload", response_model=JobCreateResponse, status_code=201)
async def create_uploaded_job(
    source_file: UploadFile = File(...),
    voice_id: str = Form("banmai"),
    burn_subtitle: bool = Form(True),
    mix_original_audio: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
) -> JobCreateResponse:
    filename = (source_file.filename or "uploaded-video.mp4").strip() or "uploaded-video.mp4"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".mp4", ".mov", ".mkv", ".webm"}:
        raise HTTPException(status_code=422, detail="Only MP4, MOV, MKV, and WebM uploads are supported.")

    content = await source_file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    max_bytes = settings.max_video_file_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=422,
            detail=f"Uploaded file is too large. This MVP supports up to {settings.max_video_file_mb} MB.",
        )

    service = JobService(db)
    user_settings = UserSettingsService.get_user_settings(user)
    job = service.create_job(
        JobCreate.model_construct(
            source_url=f"upload://{filename}",
            voice_id=voice_id,
            burn_subtitle=burn_subtitle,
            mix_original_audio=mix_original_audio,
        ),
        initial_render_config=UserSettingsService.build_job_render_defaults(
            burn_subtitle=burn_subtitle,
            mix_original_audio=mix_original_audio,
            settings_payload=user_settings,
        ),
    )

    input_video_path = service.storage.write_bytes(job.id, f"input{suffix}", content)
    service.attach_artifact(job.id, "input_video_path", input_video_path)
    service.storage.write_json(
        job.id,
        "metadata.json",
        {
            "source_url": job.source_url,
            "platform": "upload",
            "uploaded_filename": filename,
            "uploaded_size_bytes": len(content),
        },
    )
    service.log(
        job.id,
        "info",
        "created",
        "Uploaded source video attached",
        {"filename": filename, "size_bytes": len(content)},
    )
    _enqueue_job(service, job.id)
    return JobCreateResponse(job_id=job.id, status=job.status)


@router.post("/{job_id}/cancel", response_model=JobStatusResponse)
def cancel_job(job_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    service = JobService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in {"queued", "processing"}:
        raise HTTPException(status_code=409, detail="Only queued or processing jobs can be cancelled")

    task_id = job.task_id
    was_processing = job.status == "processing"
    requested = service.request_cancel(job_id)
    if task_id:
        celery_app.control.revoke(task_id, terminate=was_processing)

    return JobStatusResponse(
        job_id=requested.id,
        status=requested.status,
        progress=requested.progress,
        stage=requested.stage,
        error_message=requested.error_message,
        result_url=requested.result_url,
        subtitle_url=requested.subtitle_url,
    )


@router.post("/{job_id}/retry", response_model=JobCreateResponse)
def retry_job(job_id: str, db: Session = Depends(get_db)) -> JobCreateResponse:
    service = JobService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in {"failed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Only failed or cancelled jobs can be retried")

    retried = service.retry_job(job_id)
    _enqueue_job(service, job_id)
    return JobCreateResponse(job_id=retried.id, status=retried.status)


@router.get("", response_model=JobListResponse)
def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    status: JobStatus | None = Query(default=None),
    sort: JobSort = Query(default="newest"),
    db: Session = Depends(get_db),
) -> JobListResponse:
    jobs, total = JobService(db).list_jobs(
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        sort=sort,
    )
    items = [
        JobListItem(
            job_id=job.id,
            source_url=job.source_url,
            platform=job.platform,
            status=job.status,
            stage=job.stage,
            progress=job.progress,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
            completed_at=job.completed_at,
        )
        for job in jobs
    ]
    return JobListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/edits", response_model=JobEditListResponse)
def list_job_edits(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    tool: JobEditToolFilter = Query(default="all"),
    sort: JobEditSort = Query(default="newest"),
    db: Session = Depends(get_db),
) -> JobEditListResponse:
    edits, total = JobService(db).list_edits(
        page=page,
        page_size=page_size,
        search=search,
        tool=tool,
        sort=sort,
    )
    items = []
    for edit in edits:
        tool_group, tool_options = _split_edit_tool_summary(edit.tool_summary)
        items.append(
            JobEditListItem(
                edit_id=edit.id,
                job_id=edit.job_id,
                version_number=edit.version_number,
                tool_group=tool_group,
                tool_options=tool_options,
                result_url=edit.result_url,
                created_at=edit.created_at,
                updated_at=edit.updated_at,
            )
        )
    return JobEditListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/{job_id}/editor-state", response_model=JobEditorStateResponse)
def get_job_editor_state(job_id: str, db: Session = Depends(get_db)) -> JobEditorStateResponse:
    service = JobService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.transcript_vi_path:
        raise HTTPException(status_code=409, detail="Vietnamese transcript is not available yet")

    transcript_vi_path = _resolve_stored_path(service, job.transcript_vi_path)
    assert transcript_vi_path is not None
    segments = SubtitleService().load_segments(transcript_vi_path)
    render_config = _load_final_render_config(job_id, job, service)
    return JobEditorStateResponse(
        job_id=job_id,
        subtitle_segments=[JobSubtitleSegment.model_validate(segment) for segment in segments],
        render_config=render_config,
    )


@router.get("/{job_id}/edits/{edit_id}", response_model=JobEditDetailResponse)
def get_job_edit_detail(job_id: str, edit_id: str, db: Session = Depends(get_db)) -> JobEditDetailResponse:
    service = JobService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    edit = service.get_edit(edit_id)
    if edit is None or edit.job_id != job_id:
        raise HTTPException(status_code=404, detail="Saved edit not found")

    return JobEditDetailResponse(
        edit_id=edit.id,
        job_id=edit.job_id,
        version_number=edit.version_number,
        tool_summary=edit.tool_summary,
        config=edit.config_json or {},
        result_url=edit.result_url,
        created_at=edit.created_at,
        updated_at=edit.updated_at,
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    job = JobService(db).get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        stage=job.stage,
        error_message=job.error_message,
        result_url=job.result_url,
        subtitle_url=job.subtitle_url,
    )


@router.get("/{job_id}/logs", response_model=list[JobLogItem])
def get_job_logs(job_id: str, db: Session = Depends(get_db)) -> list[JobLogItem]:
    service = JobService(db)
    if service.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return [
        JobLogItem(
            id=log.id,
            level=log.level,
            stage=log.stage,
            message=log.message,
            data=log.data,
            created_at=log.created_at,
        )
        for log in service.list_logs(job_id)
    ]


@router.get("/{job_id}/download")
def download_result(job_id: str, db: Session = Depends(get_db)) -> FileResponse:
    service = JobService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed" or not job.output_video_path:
        raise HTTPException(status_code=409, detail="Result is not available yet")

    if service.storage.uses_object_storage():
        return RedirectResponse(service.storage.get_download_url(job.output_video_path))

    path = service.storage.resolve_path(job.output_video_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")

    return FileResponse(path, filename=f"{job_id}_vi.mp4")


@router.get("/{job_id}/subtitles")
def download_subtitles(job_id: str, db: Session = Depends(get_db)) -> FileResponse:
    service = JobService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.subtitle_path:
        raise HTTPException(status_code=409, detail="Subtitles are not available yet")

    if service.storage.uses_object_storage():
        return RedirectResponse(service.storage.get_download_url(job.subtitle_path))

    path = service.storage.resolve_path(job.subtitle_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Subtitle file not found")

    return FileResponse(path, filename=f"{job_id}_vi.srt", media_type="application/x-subrip")


def _render_job_edit(
    job_id: str,
    payload: JobEditRenderRequest,
    overwrite_edit_id: str | None,
    db: Session = Depends(get_db),
) -> JobEditRenderResponse:
    service = JobService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=409, detail="Only completed jobs can be edited")
    if not job.input_video_path or not job.tts_audio_path or not job.subtitle_path:
        raise HTTPException(status_code=409, detail="Required render artifacts are missing")

    input_video_path = _resolve_stored_path(service, job.input_video_path)
    tts_audio_path = _resolve_stored_path(service, job.tts_audio_path)
    subtitle_path = _resolve_stored_path(service, job.subtitle_path)
    original_audio_path = _resolve_stored_path(service, job.audio_path)
    transcript_vi_path = _resolve_stored_path(service, job.transcript_vi_path)
    assert input_video_path is not None
    assert tts_audio_path is not None
    assert subtitle_path is not None

    edit_id = overwrite_edit_id or str(uuid4())
    subtitle_service = SubtitleService()
    original_segments = subtitle_service.load_segments(transcript_vi_path) if transcript_vi_path else []
    render_subtitle_path = subtitle_path

    if payload.subtitle_segments:
        edited_segments = [segment.model_dump() for segment in payload.subtitle_segments]
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

    result_url = f"/api/jobs/{job_id}/edits/{edit_id}/download"
    tool_summary = _build_edit_tool_summary(
        payload,
        original_segments,
        default_burn_original_audio=bool(job.mix_original_audio),
    )
    payload_json = payload.model_dump()
    payload_json["blur_masks"] = [item.model_dump() for item in blur_masks]
    payload_json["overlays"] = [item.model_dump() for item in overlays]
    if overwrite_edit_id:
        existing_edit = service.get_edit(overwrite_edit_id)
        if existing_edit is None or existing_edit.job_id != job_id or existing_edit.is_draft:
            raise HTTPException(status_code=404, detail="Saved edit not found")
        service.update_edit(
            overwrite_edit_id,
            tool_summary=tool_summary,
            config_json=payload_json,
            output_video_path=output_path,
            result_url=result_url,
        )
    else:
        service.create_edit(
            job_id,
            edit_id=edit_id,
            tool_summary=tool_summary,
            config_json=payload_json,
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
            "overwrite_edit_id": overwrite_edit_id,
            "output_video_path": output_path,
            "tool_summary": tool_summary,
            **payload_json,
        },
    )
    return JobEditRenderResponse(job_id=job_id, edit_id=edit_id, result_url=result_url)


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


def _split_edit_tool_summary(summary: str) -> tuple[str, str]:
    parts = summary.split("::", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return summary.strip(), "Saved render"


def _load_final_render_config(job_id: str, job, service: JobService) -> dict:
    render_config = job.final_config_json
    if not isinstance(render_config, dict):
        return service.build_editor_baseline_config(job)
    return render_config


@router.post("/{job_id}/edits/render", response_model=JobEditRenderResponse)
def render_job_edit(
    job_id: str,
    payload: JobEditRenderRequest,
    overwrite_edit_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> JobEditRenderResponse:
    return _render_job_edit(job_id, payload, overwrite_edit_id, db)


@router.post("/{job_id}/edits/blur", response_model=JobEditRenderResponse)
def render_blurred_subtitles(
    job_id: str,
    payload: JobEditRenderRequest,
    db: Session = Depends(get_db),
) -> JobEditRenderResponse:
    return _render_job_edit(job_id, payload, db)


@router.get("/{job_id}/edits/{edit_id}/download")
def download_rendered_edit(job_id: str, edit_id: str, db: Session = Depends(get_db)) -> FileResponse:
    service = JobService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    edit = service.get_edit(edit_id)
    if edit is None or edit.job_id != job_id:
        raise HTTPException(status_code=404, detail="Edited output not found")

    if not edit.output_video_path:
        raise HTTPException(status_code=404, detail="Edited output not found")
    if service.storage.uses_object_storage():
        return RedirectResponse(service.storage.get_download_url(edit.output_video_path))
    path = service.storage.resolve_path(edit.output_video_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Edited output file not found")

    return FileResponse(path, filename=f"{job_id}_{edit_id[:8]}_vi_edit.mp4")


@router.get("/{job_id}/edits/render/download")
def download_legacy_rendered_edit(job_id: str) -> FileResponse:
    raise HTTPException(status_code=410, detail="Use the specific edit download URL returned by the render API.")


@router.get("/{job_id}/edits/blur/download")
def download_blurred_edit(job_id: str) -> FileResponse:
    raise HTTPException(status_code=410, detail="Use the specific edit download URL returned by the render API.")
