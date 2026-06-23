# 01 - Bootstrap

## Goal

Create the base monorepo structure and local development environment.

## Tasks

- Create `frontend/` with Vue 3, Vite, TypeScript, and pnpm.
- Create `backend/` with FastAPI and uv.
- Add `docker-compose.yml` with PostgreSQL and Redis.
- Add `.env.example` with required local configuration.
- Add root `README.md` with local setup instructions.
- Add root `.gitignore` for Python, Node, local env files, and storage artifacts.

## Acceptance Criteria

- PostgreSQL and Redis start with Docker Compose.
- Backend starts locally and exposes `GET /health`.
- Frontend starts locally and loads the home page.
- README documents the commands clearly.

