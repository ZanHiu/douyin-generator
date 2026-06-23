# 03 - Mock Worker Pipeline

## Goal

Prove the full background job lifecycle without relying on external services.

## Mock Stages

The worker should process these stages in order:

```text
fetching_video
extracting_audio
transcribing
translating
generating_subtitles
generating_tts
rendering_video
completed
```

Each stage should:

- Update `jobs.stage`.
- Update `jobs.progress`.
- Write at least one `job_logs` row.
- Create a small mock artifact where appropriate.

## Mock Artifacts

Create files under:

```text
storage/jobs/{job_id}/
```

Expected mock files:

```text
metadata.json
transcript_zh.json
transcript_vi.json
subtitles_vi.srt
voice_vi.wav.placeholder
output_vi.mp4.placeholder
```

## Failure Handling

If a mock stage raises an error:

- Set job status to `failed`.
- Set stage to `failed`.
- Set a readable `error_message`.
- Write an error log.

## Acceptance Criteria

- A job moves from `queued` to `processing` to `completed`.
- Frontend can observe progress changes through polling.
- Mock artifacts are created in the expected job folder.
- A forced mock failure produces a failed job instead of crashing the worker.

