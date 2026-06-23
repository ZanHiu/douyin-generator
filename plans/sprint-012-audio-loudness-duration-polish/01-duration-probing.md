# 01 - Duration Probing

## Goal

Read source video duration before rendering.

## Tasks

- Use `ffprobe` to read input video duration.
- Fail clearly when `ffprobe` is missing or returns invalid duration.

## Acceptance Criteria

- Render stage knows the source video duration in seconds.
