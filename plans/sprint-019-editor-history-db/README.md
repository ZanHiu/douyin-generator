# Sprint 019 - Editor History DB Persistence

## Goal

Persist rendered editor outputs in the backend database so Editor History is real, reload-safe, and shared across sessions.

## Scope

- Add a `job_edits` table and ORM model.
- Save one DB row per rendered edit with its own `edit_id` and download URL.
- Replace frontend `localStorage` edit history with server-side history.

## Done Criteria

- Each editor render creates a unique persisted edit record.
- Editor History reads from backend API, not browser storage.
- Each edit has its own download URL and file path.
- Backend and frontend validation pass.
