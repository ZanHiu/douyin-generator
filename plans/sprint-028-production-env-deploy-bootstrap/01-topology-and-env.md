# Phase 1 - Topology And Env

Define the production shape:
- `frontend`: static Vue build served behind Nginx
- `api`: FastAPI app
- `worker`: Celery worker
- `postgres`: primary relational store
- `redis`: queue broker/result backend
- `object storage`: exactly one of `r2`, `s3`, or `minio`

Implementation rules:
- keep local development flow unchanged
- production compose must not require local `uvicorn --reload` or Vite dev server
- production env examples must favor Cloudflare R2 as the recommended default
- secrets stay in env, not checked into source control

Required config groups:
- app/auth
- database
- redis
- object storage
- AI provider keys
- worker runtime
