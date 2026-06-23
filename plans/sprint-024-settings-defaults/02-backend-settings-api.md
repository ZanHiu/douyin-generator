# 02. Backend Settings API

- Store settings on the authenticated user record.
- Add:
  - `GET /api/settings/me`
  - `PUT /api/settings/me`
- Normalize missing values back to product defaults.
- Snapshot current settings onto a job at create time so old jobs remain stable after future settings edits.
