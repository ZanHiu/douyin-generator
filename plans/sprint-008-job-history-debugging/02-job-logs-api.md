# 02 - Job Logs API

## Goal

Expose logs for a single job.

## Tasks

- Add `GET /api/jobs/{job_id}/logs`.
- Return logs ordered by `created_at asc`.
- Include level, stage, message, data, created timestamp.
- Return 404 when job does not exist.

## Acceptance Criteria

- Job page can show processing/debug logs.
- API does not expose unrelated jobs.

