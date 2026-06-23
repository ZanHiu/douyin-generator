# 01 - Provider Config

## Goal

Support `TRANSLATION_PROVIDER=openrouter` through `.env`.

## Tasks

- Add OpenRouter API key config.
- Add OpenRouter model config.
- Add OpenRouter base URL and timeout config.
- Keep existing `openai` and `ollama` providers.

## Acceptance Criteria

- Missing OpenRouter API key fails clearly.
- Provider selection remains env-driven.
