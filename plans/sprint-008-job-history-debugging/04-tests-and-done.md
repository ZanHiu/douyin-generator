# 04 - Tests And Done Criteria

## Automated Tests

- Job list returns newest jobs first.
- Job logs endpoint returns logs for a job.
- Missing job logs request returns 404.
- Frontend typecheck/build passes.

## Manual Checks

- Submit multiple jobs.
- Confirm home page shows newest jobs first.
- Open a job and confirm logs appear.

## Done Criteria

- `uv run pytest --basetemp D:\tmp\pytest-douyin` passes.
- `pnpm.cmd typecheck` passes.
- `pnpm.cmd build` passes.

