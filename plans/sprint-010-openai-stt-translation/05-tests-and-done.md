# 05 - Tests And Done Criteria

## Automated Tests

- Mock transcription and translation still work when local env is configured for real providers.
- OpenAI transcription normalization drops empty segments and clamps timestamps.
- OpenAI translation parser preserves source timing.
- Translation batching splits payloads predictably.

## Manual Checks

- Add `OPENAI_API_KEY` to `.env`.
- Set `STT_PROVIDER=openai`.
- Set `TRANSLATION_PROVIDER=openai`.
- Run a short public Douyin/TikTok video.
- Confirm real `transcript_zh.json` and `transcript_vi.json` content.

## Done Criteria

- `uv run pytest --basetemp D:\tmp\pytest-douyin` passes.
- Frontend typecheck and build pass.
