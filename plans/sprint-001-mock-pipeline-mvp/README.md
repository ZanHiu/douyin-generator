# Sprint 001 - Mock Pipeline MVP

## Summary

Build the first runnable version of DouyinGenerator using mock data for AI/video-heavy steps.

This sprint should not attempt real Douyin/TikTok downloading, real STT, real translation, real TTS, or final FFmpeg rendering. The purpose is to establish the app architecture, job lifecycle, worker orchestration, database schema, frontend flow, and local development setup.

## Chosen Stack

- Frontend: Vue 3 + Vite + TypeScript
- Frontend package manager: pnpm
- Backend: FastAPI
- Python tooling: uv
- Worker: Celery
- Queue: Redis
- Database: PostgreSQL
- Migrations: Alembic
- Storage: local filesystem
- AI/video pipeline in this sprint: mock implementations

## Target Project Structure

```text
frontend/
  src/
    main.ts
    App.vue
    router/
    pages/
    components/
    lib/

backend/
  app/
    main.py
    api/
    core/
    db/
    models/
    schemas/
    services/
    workers/
  alembic/
  pyproject.toml

storage/
  jobs/

plans/
  sprint-001-mock-pipeline-mvp/

docker-compose.yml
.env.example
README.md
```

## Sprint Deliverables

- Local dev setup with PostgreSQL and Redis via Docker Compose.
- Backend health endpoint.
- Job creation API.
- Job status API.
- Celery worker that processes jobs asynchronously.
- Database tables for jobs and job logs.
- Mock pipeline stages with progress updates.
- Vue frontend home page.
- Vue frontend job progress page.
- Basic error handling and visible failed state.
- README with local run commands.

## Out Of Scope

- Real yt-dlp video download.
- Real FFmpeg extraction/rendering.
- Real OpenAI or Whisper transcription.
- Real translation provider.
- Real FPT AI TTS integration.
- Auth, payments, batch processing, subtitle editor, watermark removal, lip sync.

