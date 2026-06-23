# 01 - Provider Config

## Goal

Add provider configuration without removing existing OpenAI support.

## Tasks

- Support `STT_PROVIDER=faster_whisper`.
- Support `TRANSLATION_PROVIDER=ollama`.
- Keep `STT_PROVIDER=openai`.
- Keep `TRANSLATION_PROVIDER=openai`.

## Acceptance Criteria

- Provider selection is controlled only by `.env`.
- Unsupported provider values fail clearly.
