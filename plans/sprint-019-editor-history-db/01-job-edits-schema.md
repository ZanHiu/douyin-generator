# Job Edits Schema

- Create `job_edits` table linked to `jobs.id`.
- Store:
  - `id`
  - `job_id`
  - `tool_summary`
  - `config_json`
  - `output_video_path`
  - `result_url`
  - `created_at`
- Add ORM relationship from `Job` to `JobEdit`.
