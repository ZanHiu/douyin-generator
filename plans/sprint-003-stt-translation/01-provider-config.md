# 01 - Provider Config

## Goal

Add provider configuration for STT and translation while keeping mock defaults.

## Tasks

- Add `openai` Python dependency.
- Add settings:
  - `STT_PROVIDER=mock|openai`
  - `TRANSLATION_PROVIDER=mock|openai`
  - `OPENAI_API_KEY`
  - `TRANSCRIPTION_MODEL`
  - `TRANSLATION_MODEL`
- Keep `mock` as default provider.
- Document that backend API and worker must be restarted after env changes.

## Acceptance Criteria

- App runs without OpenAI credentials when providers are `mock`.
- OpenAI providers fail with readable message if `OPENAI_API_KEY` is missing.

