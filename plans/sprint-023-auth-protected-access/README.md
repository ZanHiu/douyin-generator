# Sprint 023 - Auth Protected Access

Goal: protect the app with a minimal production-safe login flow so only seeded admin users can access the workspace.

Scope:

- Add backend user and session tables.
- Seed one admin account from environment variables.
- Add login, logout, and current-session APIs.
- Protect all job/editor/settings APIs behind session auth.
- Add frontend login screen and route guard.
- Keep signup out of scope for this sprint.

Expected outcome:

- Unauthenticated users are redirected to `/login`.
- Authenticated users can access the existing app shell.
- Session uses secure server-side lookup instead of local-only frontend state.
- The project is ready for a private beta deploy for a single operator.
