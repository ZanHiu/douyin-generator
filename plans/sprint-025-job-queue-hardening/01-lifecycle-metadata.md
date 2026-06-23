# 01. Lifecycle Metadata

Add job fields:

- `queued_at`
- `started_at`
- `cancel_requested_at`
- `retry_count`

Use these to distinguish:

- never started
- in-flight
- cancel requested but not yet finalized
- retried attempts
