# Sprint 003 - STT And Translation

## Summary

Replace hardcoded transcript and translation stages with service-based providers.

Default providers remain `mock` so the app can run without API keys. OpenAI adapters are available through environment variables for real STT and translation.

## Phase Files

```text
01-provider-config.md
02-transcription-service.md
03-translation-service.md
04-pipeline-integration.md
05-tests-and-done.md
```

## Pipeline Shape

```text
fetching_video       real
extracting_audio     real
transcribing         mock or OpenAI
translating          mock or OpenAI
generating_subtitles mock
generating_tts       mock
rendering_video      mock
```

