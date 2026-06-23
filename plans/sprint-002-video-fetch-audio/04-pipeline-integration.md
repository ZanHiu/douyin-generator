# 04 - Pipeline Integration

## Goal

Integrate real media stages while keeping later AI/render stages mocked.

## Pipeline Shape

```text
fetching_video       real
extracting_audio     real
transcribing         mock
translating          mock
generating_subtitles mock
generating_tts       mock
rendering_video      mock
```

## Tasks

- Update worker pipeline to call `VideoResolverService` during `fetching_video`.
- Update worker pipeline to call `AudioExtractorService` during `extracting_audio`.
- Keep existing mock transcript, subtitle, TTS, and output placeholder stages.
- Add structured job logs for downloaded video and extracted audio.
- Convert expected processing errors into failed job state.

## Acceptance Criteria

- UI still shows progress from queued to completed for supported public URLs.
- Failed real media stages do not crash backend API.
- Worker logs show task received, media stage logs, and success/failure.

