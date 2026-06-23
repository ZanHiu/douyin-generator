# 02 - OpenRouter Adapter

## Goal

Use OpenRouter's OpenAI-compatible chat completions endpoint for translation.

## Tasks

- Reuse the OpenAI SDK with `base_url=https://openrouter.ai/api/v1`.
- Request JSON response format.
- Preserve source segment ids and timestamps.

## Acceptance Criteria

- `TRANSLATION_PROVIDER=openrouter` produces the same `transcript_vi.json` shape as other providers.
