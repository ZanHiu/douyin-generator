# 01 - URL Validation And Config

## Goal

Prepare Sprint 2 runtime configuration and reject unsupported URLs before the worker spends time on them.

## Tasks

- Add URL allowlist validation for Douyin/TikTok domains.
- Keep generic HTTP/HTTPS validation.
- Add media tool env vars:
  - `YTDLP_BIN`
  - `FFMPEG_BIN`
  - `FFPROBE_BIN`
- Add media limit env vars:
  - `MAX_VIDEO_DURATION_SECONDS`
  - `MAX_VIDEO_FILE_MB`
- Document that backend API and worker must be restarted after `.env` changes.

## Acceptance Criteria

- Valid Douyin/TikTok URLs can create jobs.
- Non-Douyin/TikTok URLs are rejected by API validation.
- Backend can read configured media tool paths from `.env`.

