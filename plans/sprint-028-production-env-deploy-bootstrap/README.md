# Sprint 028 - Production Env Strategy And Deploy Bootstrap

Goal: make the app deployable as a single private production stack with a clear environment strategy for API, worker, PostgreSQL, Redis, and object storage.

Scope:
- define a production runtime topology
- add production container artifacts for frontend, backend API, and Celery worker
- add readiness checks for API dependencies
- add bootstrap scripts for API and worker startup
- document one-provider object storage strategy for production
- provide a production env example and first deploy steps

Done when:
- the repo contains production Dockerfiles for frontend and backend
- the repo contains a production compose file that starts `frontend`, `api`, `worker`, `postgres`, and `redis`
- backend exposes a readiness check suitable for container healthchecks
- production env variables are documented with one clear object-storage choice at a time
- README and deploy docs explain how to bootstrap the stack
