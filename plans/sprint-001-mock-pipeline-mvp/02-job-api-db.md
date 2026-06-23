# 02 - Job API And Database

## Goal

Implement the persistent job model and the minimum API needed by the frontend.

## API

### `POST /api/jobs`

Request:

```json
{
  "source_url": "https://www.douyin.com/...",
  "voice_id": "vi_female_01",
  "burn_subtitle": true,
  "mix_original_audio": false
}
```

Response:

```json
{
  "job_id": "uuid",
  "status": "queued"
}
```

### `GET /api/jobs/{job_id}`

Response:

```json
{
  "job_id": "uuid",
  "status": "processing",
  "progress": 45,
  "stage": "translating",
  "error_message": null,
  "result_url": null,
  "subtitle_url": null
}
```

## Database

Create Alembic migration for:

- `jobs`
- `job_logs`

Use the schema from the MVP spec as the baseline.

## Acceptance Criteria

- Creating a job inserts a row in `jobs`.
- Creating a job enqueues a Celery task.
- Job status can be fetched by ID.
- Missing job returns 404.
- Basic validation rejects empty or malformed URLs.

