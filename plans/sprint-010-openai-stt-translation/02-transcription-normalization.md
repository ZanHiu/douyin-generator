# 02 - Transcription Normalization

## Goal

Normalize OpenAI transcription output into the existing `transcript_zh.json` shape.

## Tasks

- Save raw OpenAI response to `transcript_zh_raw.json`.
- Normalize segment `id`, `start`, `end`, and `text`.
- Drop empty transcript segments.
- Clamp negative timestamps to zero.

## Acceptance Criteria

- `transcript_zh.json` has stable segment data for translation.
- Empty OpenAI output marks the job as failed with a readable error.
