#!/bin/sh
set -eu

export PYTHONPATH="/app/backend"
uv run python scripts/wait_for_services.py
uv run alembic upgrade head
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-1}"
