# 01. Auth Data Model

- Add `users` table:
  - `id`
  - `email`
  - `password_hash`
  - `is_active`
  - `is_admin`
  - timestamps
- Add `auth_sessions` table:
  - `id`
  - `user_id`
  - `token_hash`
  - `expires_at`
  - `created_at`
- Use hashed session tokens in DB.
- Keep auth isolated from job/edit tables for now.
