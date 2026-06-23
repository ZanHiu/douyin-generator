# API And UI

- Update render API to return:
  - `job_id`
  - `edit_id`
  - `result_url`
- Persist every render into `job_edits`.
- Add paginated `GET /api/jobs/edits`.
- Update `EditorLandingPage` to load history from API instead of `localStorage`.
