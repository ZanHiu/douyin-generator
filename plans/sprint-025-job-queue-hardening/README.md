# Sprint 025 - Job Queue Hardening

Goal: make create/cancel/retry behavior more predictable by hardening job lifecycle metadata, stale-job recovery, and Celery dispatch settings.

Scope:

- Add queue lifecycle fields to jobs.
- Track when a job was queued, started, and cancellation was requested.
- Improve Celery task dispatch configuration for single-worker stability.
- Recover stale `queued`, `processing`, and `cancelling` jobs on startup.
- Centralize enqueue logic so create/retry follow the same path.

Expected outcome:

- Jobs no longer stay stuck in stale `cancelling` after a restart.
- Retry/create use one dispatch flow.
- The system has enough metadata to explain queue behavior and recover interrupted work.
