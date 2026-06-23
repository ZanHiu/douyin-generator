# Phase 2 - Reverse Proxy And Domain

Objective:

- document how to expose the app on a real domain with HTTPS
- avoid exposing the internal frontend port publicly when a reverse proxy is present

Deliverables:

- `deploy/oracle/Caddyfile.example`
- compose support for binding frontend to `127.0.0.1`
- production env documentation for `PUBLIC_BASE_URL` and `FRONTEND_ORIGIN`
