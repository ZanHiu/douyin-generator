# Sprint 006 - Video Render

## Summary

Replace the final video placeholder with a real FFmpeg render step.

The output video uses the downloaded source video, generated `voice_vi.wav`, and generated `subtitles_vi.srt`.

## Phase Files

```text
01-video-renderer-service.md
02-pipeline-integration.md
03-tests-and-done.md
```

## Pipeline Shape

```text
fetching_video       real
extracting_audio     real
transcribing         mock or OpenAI
translating          mock or OpenAI
generating_subtitles real
generating_tts       real WAV artifact with mock provider
rendering_video      real
```

