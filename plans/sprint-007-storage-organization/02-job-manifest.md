# 02 - Job Manifest

## Goal

Add a small file inside each job folder so the folder is self-describing.

## Tasks

- Write `job_manifest.json` after job creation.
- Include:
  - `job_id`
  - `created_at`
  - `source_url`
  - `platform`
  - `status`
  - selected options

## Acceptance Criteria

- New job folder contains `job_manifest.json`.
- Manifest helps identify job source without opening the database.

