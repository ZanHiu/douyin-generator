# 05 - Tests And Done Criteria

## Automated Tests

- Voice polish FFmpeg args include volume, `apad`, and `atrim`.
- Subtitle path escaping still works.
- Existing backend tests pass.

## Manual Checks

- Run a completed job.
- Confirm `voice_vi_render.wav` exists.
- Confirm output video duration matches input duration more closely.
- Confirm voice is louder than before.

## Done Criteria

- `uv run pytest --basetemp D:\tmp\pytest-douyin` passes.
- Frontend typecheck/build pass.
