# DouyinGenerator

Web app for turning a Douyin/TikTok video into a Vietnamese dubbed and subtitled output.

## What It Does

- Accepts a Douyin/TikTok URL or uploaded source video
- Extracts audio and generates a source transcript
- Translates transcript content into Vietnamese
- Produces subtitle files and synthesized Vietnamese voice audio
- Renders a final localized video
- Includes a browser-based job viewer and editor workflow

## Stack

- Frontend: Vue 3 + Vite + TypeScript
- Backend: FastAPI
- Worker: Celery
- Queue: Redis
- Database: PostgreSQL
- Storage: local filesystem or S3-compatible object storage

## Repository Layout

```text
frontend/   Vue application
backend/    FastAPI API, worker, and pipeline services
docs/       Maintainer and deployment documentation
plans/      Sprint and implementation planning notes
```

## Public Quick Start

Prerequisites:

- Node.js 20+
- pnpm
- Python 3.11+
- uv
- Docker
- yt-dlp
- FFmpeg / ffprobe

Basic local setup:

```powershell
Copy-Item .env.example .env
docker compose up -d

cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In another terminal:

```powershell
cd backend
uv run celery -A app.workers.celery_app.celery_app worker --loglevel=info --pool=threads --concurrency=2
```

In another terminal:

```powershell
cd frontend
pnpm install
pnpm dev
```

Open:

```text
http://localhost:5173
```

## Environment

- Local development uses `.env` copied from `.env.example`
- Production-style deployments use `.env.production` copied from `.env.production.example`

Do not commit real credentials, provider keys, cookies, or production connection strings.

## Maintainer Docs

Detailed setup, deployment, storage, and provider notes were moved out of this public-facing README:

- [Maintainer setup](./docs/maintainer-setup.md)
- [Production deploy](./docs/deploy-production.md)
- [Netlify + Northflank deploy](./docs/deploy-netlify-northflank.md)
- [Oracle VPS deploy](./docs/deploy-oracle-vps.md)

## Notes

- This repository may contain templates and example configuration values, but those are placeholders only.
- If this project is intended to stay public, keep operational specifics minimal in `README.md` and store deeper runbooks under `docs/`.
