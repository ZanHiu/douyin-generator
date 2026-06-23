# 01 - Storage Folder Naming

## Goal

Create readable storage folders for new jobs.

## Tasks

- Add `jobs.storage_dir` column.
- Generate folder names:

```text
YYYYMMDD-HHMMSS_{platform}_{short_job_id}
```

- Store full storage path in `jobs.storage_dir`.
- Make `StorageService.job_dir(job_id)` resolve DB-backed folder when available.
- Fall back to old `storage/jobs/{job_id}` for legacy jobs.

## Acceptance Criteria

- New job folders are easy to sort by time.
- Existing jobs are not moved or broken.

