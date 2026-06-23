# 01 - Job List API

## Goal

Expose recent jobs through the API so the frontend can show job history.

## Tasks

- Add `GET /api/jobs`.
- Return recent jobs ordered by `created_at desc`.
- Include job ID, source URL, platform, status, stage, progress, error message, created/updated/completed timestamps.
- Limit response size with a query parameter, default 20, max 100.

## Acceptance Criteria

- Frontend can fetch recent jobs.
- API does not expose local artifact paths.

