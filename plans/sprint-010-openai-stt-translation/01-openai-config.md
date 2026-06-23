# 01 - OpenAI Config

## Goal

Document and support the environment variables needed for real OpenAI STT and translation.

## Tasks

- Keep `STT_PROVIDER=mock` and `TRANSLATION_PROVIDER=mock` available.
- Support `STT_PROVIDER=openai`.
- Support `TRANSLATION_PROVIDER=openai`.
- Add timeout and translation batch size config.

## Acceptance Criteria

- Missing `OPENAI_API_KEY` fails with a readable `ProcessingError`.
- Mock providers still work without network calls.
