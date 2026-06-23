# 05 - Tests And Done Criteria

## Backend Tests

- `GET /health` returns OK.
- `POST /api/jobs` creates a queued job.
- `GET /api/jobs/{job_id}` returns the job.
- Invalid job ID returns 404.
- Invalid URL returns validation error.
- Mock worker success marks job completed.
- Mock worker failure marks job failed.

## Frontend Checks

- Home page renders.
- Submit button calls job API.
- Successful submit navigates to job page.
- Job page renders queued, processing, completed, and failed states.

## Manual Done Criteria

- `docker compose up` starts PostgreSQL and Redis.
- Backend can run locally.
- Celery worker can run locally.
- Frontend can run locally.
- A mock job can be submitted from the UI.
- The UI shows progress and completion.
- Mock job artifacts appear under `storage/jobs/{job_id}`.

