# 04 - Pipeline Artifacts

## Goal

Make real STT and translation debuggable from local job folders.

## Tasks

- Write `transcript_zh_raw.json`.
- Write `transcript_zh.json`.
- Write `transcript_vi_raw.json`.
- Write `transcript_vi.json`.

## Acceptance Criteria

- A failed or suspicious result can be inspected from `storage/jobs`.
- Subtitle, TTS, and render stages continue using the normalized files.
