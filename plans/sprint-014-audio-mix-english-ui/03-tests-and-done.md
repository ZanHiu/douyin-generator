# 03 - Tests & Done

## Verification

- `uv run python -m compileall app tests`
- `uv run ruff check app tests`
- `uv run pytest --basetemp .pytest-tmp`
- `pnpm typecheck`
- `pnpm build`

## Manual Test

1. Run a job with original audio mix disabled.
2. Confirm final output has Vietnamese voice.
3. Run a job with original audio mix enabled.
4. Confirm final output has Vietnamese voice with source audio quietly underneath.
