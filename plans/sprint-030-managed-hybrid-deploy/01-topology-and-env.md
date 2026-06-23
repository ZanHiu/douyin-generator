# Phase 1 - Topology And Env

## Goal

Lock the recommended managed topology and document which env variables belong to which platform.

## Decisions

- Netlify serves only the Vue frontend build.
- Northflank runs two services from the same backend image:
  - API
  - worker
- Supabase provides external Postgres.
- Upstash provides external Redis.
- Cloudflare R2 remains the durable artifact store.

## Env split

### Netlify

- `VITE_API_BASE_URL`

### Northflank API and worker

- `DATABASE_URL`
- `REDIS_URL`
- `PUBLIC_BASE_URL`
- `FRONTEND_ORIGIN`
- `FRONTEND_ORIGINS`
- `AUTH_COOKIE_*`
- storage env
- AI provider env

## Done

- one managed env example exists
- one deploy doc explains how values are split across platforms
