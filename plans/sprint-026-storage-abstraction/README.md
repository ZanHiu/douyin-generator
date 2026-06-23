# Sprint 026 - Storage Abstraction

Goal: decouple persisted job/edit artifact references from absolute local filesystem paths, while keeping the current local storage behavior unchanged.

Scope:

- Introduce storage backend config with `local` as the current default.
- Normalize persisted artifact references into storage keys like `jobs/...` and `edits/...`.
- Resolve stored keys back into local filesystem paths at API and service boundaries.
- Keep backward compatibility with legacy absolute-path rows already stored in the database.

Expected outcome:

- The database stops depending on machine-specific absolute paths for new records.
- Existing jobs and edits continue to work without a data migration.
- The backend has a clean seam for a future object storage backend.
