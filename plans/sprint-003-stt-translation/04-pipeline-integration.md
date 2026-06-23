# 04 - Pipeline Integration

## Goal

Wire STT and translation services into the worker pipeline.

## Tasks

- Inject `TranscriptionService` into the pipeline.
- Inject `TranslationService` into the pipeline.
- Replace hardcoded transcript and translation blocks.
- Keep subtitle, TTS, and render stages mocked.
- Persist `transcript_zh_path` and `transcript_vi_path`.
- Add job logs for transcription and translation artifacts.

## Acceptance Criteria

- Existing Sprint 2 media flow still works.
- Transcribing and translating stages use configured providers.
- Later mock stages still complete the job.

