# 03. Tests And Done

- Run backend compile checks.
- Verify:
  - create -> queued metadata set
  - processing -> started metadata set
  - cancel queued -> immediate cancelled
  - cancel processing -> cancelling metadata set
  - retry -> retry count increments and task is re-enqueued
  - stale cancelling / orphaned processing recovered on startup
