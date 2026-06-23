# 02. Dispatch And Recovery

- Move job enqueue behavior into one helper.
- Configure Celery with:
  - `task_track_started`
  - `task_acks_late`
  - `worker_prefetch_multiplier = 1`
- On API startup and worker startup:
  - finalize stale cancelling jobs after grace period
  - mark orphaned processing jobs failed if their task no longer exists
  - clear orphaned queued task ids so jobs can be re-dispatched safely
