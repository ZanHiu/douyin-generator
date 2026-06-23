#!/bin/sh
set -eu

export PYTHONPATH="/app/backend"

uv run python scripts/wait_for_services.py
exec uv run celery -A app.workers.celery_app.celery_app worker --loglevel="${CELERY_LOG_LEVEL:-info}" --pool="${CELERY_WORKER_POOL:-threads}" --concurrency="${CELERY_WORKER_CONCURRENCY:-2}"
