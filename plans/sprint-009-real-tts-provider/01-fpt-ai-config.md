# 01 - FPT AI Config

## Goal

Add environment configuration for FPT AI TTS.

## Tasks

- Add `TTS_PROVIDER=fpt_ai`.
- Add `FPT_AI_API_KEY`.
- Add `FPT_AI_VOICE_ID`.
- Add `FPT_AI_TTS_URL`.
- Add `TTS_POLL_ATTEMPTS` and `TTS_POLL_INTERVAL_SECONDS`.

## Acceptance Criteria

- Mock TTS remains the default.
- Missing FPT key fails with readable `ProcessingError`.

