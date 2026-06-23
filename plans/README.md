# DouyinGenerator Plans

This folder contains implementation plans organized by sprint.

The original product requirements are kept locally in:

```text
docs/product-spec.md
```

The `docs/` folder is intentionally ignored by git.

## Sprint Roadmap

### Sprint 001 - Mock Pipeline MVP

Goal: scaffold the full app and prove the end-to-end job flow with mock data.

Folder:

```text
plans/sprint-001-mock-pipeline-mvp/
```

Expected outcome:

- Vue + Vite frontend can submit a URL.
- FastAPI backend can create and return job status.
- Celery worker can process a job through mocked stages.
- PostgreSQL stores jobs and logs.
- Redis queues background work.
- Local storage contains mock artifacts.
- UI can show queued, processing, completed, and failed states.

### Future Sprints

Future sprint folders should be created only when the sprint is ready to plan.

Recommended naming:

```text
plans/sprint-010-audio-render-polish/
plans/sprint-011-hardening/
```

### Sprint 002 - Video Fetch And Audio Extraction

Goal: replace the first two mock stages with real `yt-dlp` video download and FFmpeg audio extraction.

Folder:

```text
plans/sprint-002-video-fetch-audio/
```

### Sprint 003 - STT And Translation

Goal: replace hardcoded transcript and translation stages with provider-based services, keeping mock defaults and adding optional OpenAI adapters.

Folder:

```text
plans/sprint-003-stt-translation/
```

### Sprint 004 - Subtitle Generation

Goal: replace the hardcoded subtitle stage with real SRT generation from `transcript_vi.json`.

Folder:

```text
plans/sprint-004-subtitle-generation/
```

### Sprint 005 - TTS Audio

Goal: replace the TTS placeholder with a real `voice_vi.wav` artifact generated from translated segments.

Folder:

```text
plans/sprint-005-tts-audio/
```

### Sprint 006 - Video Render

Goal: replace the final video placeholder with a real FFmpeg-rendered `output_vi.mp4`.

Folder:

```text
plans/sprint-006-video-render/
```

### Sprint 007 - Storage Organization

Goal: make local job folders readable and self-describing while preserving legacy job folders.

Folder:

```text
plans/sprint-007-storage-organization/
```

### Sprint 008 - Job History And Debugging

Goal: add recent jobs and per-job logs APIs/UI so local testing is easier.

Folder:

```text
plans/sprint-008-job-history-debugging/
```

### Sprint 009 - Real TTS Provider

Goal: add FPT AI TTS adapter to generate real Vietnamese voice audio.

Folder:

```text
plans/sprint-009-real-tts-provider/
```
