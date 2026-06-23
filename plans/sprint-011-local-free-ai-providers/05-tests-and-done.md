# 05 - Tests And Done Criteria

## Automated Tests

- Existing OpenAI parser tests still pass.
- Local provider normalization and parsing reuse the same stable shapes.
- Backend test suite passes without requiring real Ollama or Whisper model downloads.

## Manual Checks

- Run `uv sync`.
- Install/start Ollama.
- Run `ollama pull qwen3:4b`.
- Run a short public video job with local STT/translation.

## Done Criteria

- `uv run pytest --basetemp D:\tmp\pytest-douyin` passes.
- Frontend typecheck and build pass.
