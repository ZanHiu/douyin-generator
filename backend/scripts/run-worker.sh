#!/bin/sh
set -eu

export PYTHONPATH="/app/backend"

if [ -n "${YTDLP_COOKIES_B64:-}" ]; then
  cookies_file="${YTDLP_COOKIES_FILE:-/tmp/douyin-cookies.txt}"
  mkdir -p "$(dirname "$cookies_file")"
  printf '%s' "$YTDLP_COOKIES_B64" | base64 -d > "$cookies_file"
  chmod 600 "$cookies_file"
  export YTDLP_COOKIES_FILE="$cookies_file"
fi

uv run python scripts/wait_for_services.py
exec uv run celery -A app.workers.celery_app.celery_app worker --loglevel="${CELERY_LOG_LEVEL:-info}" --pool="${CELERY_WORKER_POOL:-threads}" --concurrency="${CELERY_WORKER_CONCURRENCY:-2}"
