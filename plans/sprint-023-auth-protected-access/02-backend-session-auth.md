# 02. Backend Session Auth

- Add env config for:
  - admin email
  - admin password
  - session cookie name
  - session duration
  - secure-cookie toggle
- Seed admin user on app startup if env values exist.
- Add auth utilities:
  - password hashing/verify
  - random session token generation
  - cookie write/clear helpers
- Add endpoints:
  - `POST /api/auth/login`
  - `POST /api/auth/logout`
  - `GET /api/auth/me`
- Protect all `/api/jobs/**` routes with authenticated-session dependency.
