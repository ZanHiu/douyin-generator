# DouyinGenerator

MVP web app for turning a Douyin/TikTok URL into a Vietnamese dubbed and subtitled video.

The current MVP downloads a source video, extracts audio, can run STT/translation through mock or OpenAI providers, generates an SRT subtitle file, creates a WAV narration artifact, and renders a final MP4.

## Stack

- Frontend: Vue 3 + Vite + TypeScript
- Backend: FastAPI
- Worker: Celery
- Queue: Redis
- Database: PostgreSQL
- Migrations: Alembic
- Storage: local filesystem or S3-compatible object storage

## Production Storage

The app supports one storage backend at a time:

- `local`
- `r2`
- `s3`
- `minio`

Recommended:

- `r2` for the simplest public deployment path
- `s3` if the rest of the stack lives on AWS
- `minio` only if you want to self-host object storage

Important:

- Do not configure all three together.
- Set `STORAGE_BACKEND` to one provider only.
- Keep the Python `minio` dependency. The backend uses it as the shared S3-compatible client for `r2`, `s3`, and `minio`.

## Production Bootstrap

Sprint 028 adds a first private-production bootstrap:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.production.yml`
- `.env.production.example`
- `docs/deploy-production.md`

Recommended production path:

- `frontend` on port `8080`
- `api` and `worker` behind Docker Compose
- `postgres` and `redis` inside the same private compose network
- `r2` as the durable object storage backend

Managed low-cost alternative:

- `Netlify` for the frontend
- `Northflank` for API
- `Supabase` for PostgreSQL
- `Upstash` for Redis
- `Cloudflare R2` for object storage

Recommended practical Douyin setup:

- `frontend` local or deployed
- `api` on `Northflank`
- `worker` local on your machine
- `Supabase` for PostgreSQL
- `Upstash` for Redis
- `Cloudflare R2` for object storage

Why:

- Douyin metadata/download requests are more likely to be blocked from cloud datacenter IPs
- running the worker locally lets `yt-dlp` use your local network environment directly
- the rest of the system can stay managed in the cloud

Quick start:

```powershell
Copy-Item .env.production.example .env.production
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build
```

For a single-VM Oracle deploy path, see:

```text
docs/deploy-oracle-vps.md
```

For the managed hybrid deploy path, see:

```text
docs/deploy-netlify-northflank.md
```

The API now exposes:

- `/health`
- `/health/live`
- `/health/ready`

## Prerequisites

- Node.js 20+
- pnpm
- Python 3.11+
- uv
- Docker Desktop or compatible Docker runtime
- yt-dlp
- FFmpeg and ffprobe

## Frontend API Base URL

Local development keeps using relative `/api` requests by default.

For a separately hosted frontend, set:

```env
VITE_API_BASE_URL=https://api.your-domain.example
```

The frontend uses that value for:

- API requests
- final job download links
- edited video download links
- preview video URLs returned by the API

## Local Setup

Copy environment variables:

```powershell
Copy-Item .env.example .env
```

Start database and queue:

```powershell
docker compose up -d
```

## Object Storage Config

Local development:

```env
STORAGE_BACKEND=local
STORAGE_ROOT=./storage
```

Recommended production example with Cloudflare R2:

```env
STORAGE_BACKEND=r2
STORAGE_BUCKET=douyin-generator
STORAGE_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
STORAGE_REGION=
STORAGE_ACCESS_KEY=<r2-access-key>
STORAGE_SECRET_KEY=<r2-secret-key>
STORAGE_PREFIX=production
STORAGE_PUBLIC_URL_BASE=
STORAGE_SECURE=true
STORAGE_PRESIGN_EXPIRY_SECONDS=3600
```

AWS S3 example:

```env
STORAGE_BACKEND=s3
STORAGE_BUCKET=douyin-generator-prod
STORAGE_ENDPOINT_URL=https://s3.ap-southeast-1.amazonaws.com
STORAGE_REGION=ap-southeast-1
STORAGE_ACCESS_KEY=<aws-access-key>
STORAGE_SECRET_KEY=<aws-secret-key>
STORAGE_PREFIX=production
STORAGE_PUBLIC_URL_BASE=
STORAGE_SECURE=true
```

MinIO example:

```env
STORAGE_BACKEND=minio
STORAGE_BUCKET=douyin-generator
STORAGE_ENDPOINT_URL=http://localhost:9000
STORAGE_REGION=
STORAGE_ACCESS_KEY=<minio-access-key>
STORAGE_SECRET_KEY=<minio-secret-key>
STORAGE_PREFIX=production
STORAGE_PUBLIC_URL_BASE=
STORAGE_SECURE=false
```

Install backend dependencies:

```powershell
cd backend
uv sync
```

Run migrations:

```powershell
uv run alembic upgrade head
```

Start backend:

```powershell
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Start worker in another terminal:

```powershell
cd backend
uv run celery -A app.workers.celery_app.celery_app worker --loglevel=info --pool=solo
uv run celery -A app.workers.celery_app.celery_app worker --loglevel=info --pool=threads --concurrency=2
set "APP_ENV=production" && .\.venv\Scripts\celery.exe -A app.workers.celery_app.celery_app worker --loglevel=info --pool=threads --concurrency=2
```

Install and start frontend:

```powershell
cd frontend
pnpm install
pnpm dev
```

Open:

```text
http://localhost:5173
```

## Hybrid Remote API + Local Worker

This is the recommended operating mode when Douyin blocks cloud worker IPs.

Keep:

- API remote on `Northflank`
- PostgreSQL remote on `Supabase`
- Redis remote on `Upstash`
- object storage remote on `Cloudflare R2`

Run locally:

- `Celery worker`

How to wire it:

1. Put your cloud values into local `.env`:

```env
DATABASE_URL=postgresql+psycopg://<supabase-connection>
REDIS_URL=rediss://<upstash-connection>?ssl_cert_reqs=required
STORAGE_BACKEND=r2
STORAGE_BUCKET=<r2-bucket>
STORAGE_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
STORAGE_ACCESS_KEY=<r2-access-key>
STORAGE_SECRET_KEY=<r2-secret-key>
STORAGE_PREFIX=production
```

2. Keep the same provider settings in local `.env` that production uses, for example:

```env
STT_PROVIDER=faster_whisper
TRANSLATION_PROVIDER=nine_router
TTS_PROVIDER=fpt_ai
```

3. Start only the local worker:

```powershell
cd backend
uv run celery -A app.workers.celery_app.celery_app worker --loglevel=info --pool=threads --concurrency=2
```

4. Do not run the worker on Northflank while testing this mode.

Result:

- frontend talks to remote API
- remote API enqueues jobs in remote Redis
- local worker consumes those jobs and uploads artifacts to R2

## Sprint 001 Behavior

- Submitting a URL creates a queued job.
- The Celery worker downloads the source video, extracts audio, runs configured STT/translation providers, generates SRT subtitles, creates a WAV narration artifact, then renders `output_vi.mp4`.
- Job progress is persisted to PostgreSQL.
- Artifacts are written to `storage/jobs/{job_id}`.
- The frontend polls job status every 2 seconds.

## Sprint 002 Media Tools

Verify media tools are available before running real URL jobs:

```powershell
yt-dlp --version
ffmpeg -version
ffprobe -version
```

If they are installed but not on PATH, set these in `.env`:

```env
YTDLP_BIN=C:\path\to\yt-dlp.exe
FFMPEG_BIN=C:\path\to\ffmpeg.exe
FFPROBE_BIN=C:\path\to\ffprobe.exe
```

After changing `.env`, restart both backend API and Celery worker.

## Sprint 003 STT And Translation

Default local providers are mock:

```env
STT_PROVIDER=mock
TRANSLATION_PROVIDER=mock
```

To use OpenAI providers, set:

```env
STT_PROVIDER=openai
TRANSLATION_PROVIDER=openai
OPENAI_API_KEY=your_api_key
TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
TRANSLATION_MODEL=gpt-4o-mini
```

After changing provider env vars, restart both backend API and Celery worker.

## Sprint 004 Subtitle Generation

The `generating_subtitles` stage now creates `subtitles_vi.srt` from `transcript_vi.json`.

Expected subtitle artifact:

```text
storage/jobs/{job_id}/subtitles_vi.srt
```

## Sprint 005 TTS Audio

The `generating_tts` stage now creates a valid WAV artifact using the default mock TTS provider:

```text
storage/jobs/{job_id}/voice_vi.wav
storage/jobs/{job_id}/tts/000.wav
```

The mock provider creates silent audio aligned to translated segment timestamps. Real Vietnamese TTS provider integration comes later.

## Sprint 006 Video Render

The `rendering_video` stage now creates a real MP4:

```text
storage/jobs/{job_id}/output_vi.mp4
```

The current default TTS provider is still mock, so the rendered video uses silent Vietnamese narration audio until a real TTS provider is integrated.

## Sprint 007 Storage Organization

New jobs use readable folder names:

```text
storage/jobs/YYYYMMDD-HHMMSS_{platform}_{short_job_id}/
```

Each new job folder includes:

```text
job_manifest.json
```

Older UUID-only folders are still valid and are not moved automatically.

## Sprint 008 Job History And Logs

The API exposes recent jobs and per-job logs:

```text
GET /api/jobs
GET /api/jobs/{job_id}/logs
```

The frontend home page shows recent jobs, and the job detail page shows processing logs.

## Sprint 009 Real TTS Provider

Default TTS remains mock:

```env
TTS_PROVIDER=mock
```

To use FPT AI TTS, set:

```env
TTS_PROVIDER=fpt_ai
FPT_AI_API_KEY=your_fpt_ai_key
FPT_AI_VOICE_ID=banmai
FPT_AI_SPEED=0
FPT_AI_FORMAT=mp3
FPT_AI_TTS_URL=https://api.fpt.ai/hmi/tts/v5
```

The app will create:

```text
storage/jobs/{job_folder}/tts/000.mp3
storage/jobs/{job_folder}/tts/000.wav
storage/jobs/{job_folder}/voice_vi.wav
```

After changing TTS env vars, restart both backend API and Celery worker.

## Sprint 010 OpenAI STT And Translation

To transcribe and translate real video audio, set:

```env
STT_PROVIDER=openai
TRANSLATION_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
TRANSLATION_MODEL=gpt-4o-mini
OPENAI_REQUEST_TIMEOUT_SECONDS=120
OPENAI_TRANSLATION_BATCH_SIZE=20
```

The worker will create:

```text
storage/jobs/{job_folder}/transcript_zh_raw.json
storage/jobs/{job_folder}/transcript_zh.json
storage/jobs/{job_folder}/transcript_vi_raw.json
storage/jobs/{job_folder}/transcript_vi.json
```

After changing OpenAI env vars, restart both backend API and Celery worker.

## Sprint 011 Local Free AI Providers

OpenAI remains supported, but local/free providers are available:

```env
STT_PROVIDER=faster_whisper
TRANSLATION_PROVIDER=ollama
```

Install backend dependencies after pulling this sprint:

```powershell
cd backend
uv sync
```

Faster Whisper config:

```env
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

Ollama config:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
OLLAMA_REQUEST_TIMEOUT_SECONDS=180
OLLAMA_TRANSLATION_BATCH_SIZE=5
```

Before running a job with Ollama, install Ollama, then pull the model:

```powershell
ollama pull qwen3:8b
```

After changing provider env vars, restart both backend API and Celery worker.

## Sprint 012 Audio Loudness And Duration Polish

Before rendering the final MP4, the worker creates a render-ready voice track:

```text
storage/jobs/{job_folder}/voice_vi_render.wav
```

This file is generated from `voice_vi.wav` by:

- increasing voice loudness
- padding silence to match the source video duration
- trimming audio if it exceeds the source video duration

Adjust voice loudness with:

```env
VOICE_VOLUME_MULTIPLIER=2.0
VOICE_LOUDNORM_TARGET_I=-14.0
VOICE_LOUDNORM_TARGET_TP=-1.5
VOICE_LOUDNORM_TARGET_LRA=11.0
```

Increase this value if the dubbed voice is still too quiet, for example `2.5` or `3.0`.

## Sprint 013 OpenRouter Translation Provider

OpenRouter can replace Ollama for higher quality cloud translation while keeping local STT:

```env
STT_PROVIDER=faster_whisper
TRANSLATION_PROVIDER=openrouter
TTS_PROVIDER=fpt_ai
```

Configure OpenRouter:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=qwen/qwen3-next-80b-a3b-instruct:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_REQUEST_TIMEOUT_SECONDS=120
OPENROUTER_TRANSLATION_BATCH_SIZE=120
OPENROUTER_RATE_LIMIT_RETRY_ATTEMPTS=8
OPENROUTER_RATE_LIMIT_SLEEP_SECONDS=60
OPENROUTER_HTTP_REFERER=
OPENROUTER_APP_TITLE=DouyinGenerator
```

After changing provider env vars, restart both backend API and Celery worker.

## 9Router Local Translation Provider

9Router can be used as a local OpenAI-compatible router. Start 9Router first, configure a single Qwen provider/model in its dashboard, then use:

```env
TRANSLATION_PROVIDER=nine_router
NINE_ROUTER_MODEL=qwen
NINE_ROUTER_BASE_URL=http://localhost:20128/v1
NINE_ROUTER_REQUEST_TIMEOUT_SECONDS=180
NINE_ROUTER_TRANSLATION_BATCH_SIZE=120
```

Keep routing pinned to one model/provider for a whole video. Automatic fallback between different models can make subtitle translation inconsistent.

## Env Files

This repo intentionally uses only two real env contexts:

- `.env` for local development
- `.env.production` for production-like Docker Compose and managed deploy values

And two matching templates:

- `.env.example`
- `.env.production.example`

Northflank, Netlify, Supabase, Upstash, and R2 should all be configured from the same production key set shown in `.env.production.example`.
