# 03 - Tests And Done Criteria

## Automated Tests

- New job gets `storage_dir`.
- Storage folder name contains timestamp, platform, and short job ID.
- `job_manifest.json` is written.
- Existing job fallback path still resolves to `storage/jobs/{job_id}`.

## Manual Checks

- Submit a new job from the frontend.
- Confirm folder name is readable.
- Confirm `job_manifest.json` exists.

## Done Criteria

- `uv run alembic upgrade head` succeeds.
- `uv run pytest --basetemp D:\tmp\pytest-douyin` passes.

