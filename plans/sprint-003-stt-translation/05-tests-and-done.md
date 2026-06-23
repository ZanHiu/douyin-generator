# 05 - Tests And Done Criteria

## Automated Tests

- Mock transcription writes `transcript_zh.json`.
- Mock translation writes `transcript_vi.json`.
- Pipeline test passes with fake media services and default mock AI providers.
- Unsupported provider value raises readable processing error.
- Missing OpenAI API key raises readable processing error.

## Manual Checks

- With mock providers, a public Douyin/TikTok URL still completes.
- With OpenAI providers and a valid API key, `transcript_zh.json` is generated from `audio.wav`.
- With OpenAI providers and a valid API key, `transcript_vi.json` contains Vietnamese translations.

## Done Criteria

- `uv run pytest --basetemp D:\tmp\pytest-douyin` passes.
- Default local app still works without API keys.
- OpenAI integration is configurable through `.env`.

