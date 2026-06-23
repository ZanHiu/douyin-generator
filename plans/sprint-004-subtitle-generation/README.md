# Sprint 004 - Subtitle Generation

## Summary

Replace the hardcoded subtitle stage with a real `SubtitleService` that generates SRT from `transcript_vi.json`.

TTS and final video rendering remain mocked in this sprint.

## Phase Files

```text
01-subtitle-service.md
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
generating_tts       mock
rendering_video      mock
```

