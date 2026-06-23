# Northflank Service Notes

Use the existing `backend/Dockerfile` for both services.

## API service

- Build context: repo root
- Dockerfile path: `backend/Dockerfile`
- Port: `8000`
- Start command:

```bash
/bin/sh /app/backend/scripts/run-api.sh
```

- Health check path:

```text
/health/ready
```

## Worker service

- Build context: repo root
- Dockerfile path: `backend/Dockerfile`
- Start command:

```bash
/bin/sh /app/backend/scripts/run-worker.sh
```

## Important

- both services must receive the same env for DB, Redis, storage, and AI providers
- only the API service needs:
  - `PUBLIC_BASE_URL`
  - `FRONTEND_ORIGIN`
  - `FRONTEND_ORIGINS`
  - `AUTH_COOKIE_*`
- if you use Supabase and Upstash, keep `DATABASE_URL` and `REDIS_URL` external; do not provision local Postgres/Redis inside Northflank for this stack
