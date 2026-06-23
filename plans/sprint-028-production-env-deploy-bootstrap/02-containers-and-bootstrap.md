# Phase 2 - Containers And Bootstrap

Add:
- backend Dockerfile with FFmpeg and yt-dlp available inside the image
- frontend Dockerfile with production build output served by Nginx
- startup scripts for API and worker
- production compose file with healthchecks and startup ordering

Behavior:
- API waits for PostgreSQL and Redis, runs Alembic, then starts Uvicorn
- worker waits for PostgreSQL and Redis, then starts Celery
- frontend proxies `/api` and `/health` to the API service inside the compose network
- healthchecks should fail fast when API dependencies are unavailable
