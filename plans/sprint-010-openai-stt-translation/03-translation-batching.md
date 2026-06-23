# 03 - Translation Batching

## Goal

Translate transcript segments with OpenAI without letting model output modify timestamps.

## Tasks

- Send transcript segments in configurable batches.
- Ask OpenAI for concise Vietnamese suitable for subtitles and TTS.
- Parse JSON responses.
- Preserve original ids and timestamps from the source transcript.

## Acceptance Criteria

- `transcript_vi.json` keeps original timing.
- Missing or empty translations fail clearly.
