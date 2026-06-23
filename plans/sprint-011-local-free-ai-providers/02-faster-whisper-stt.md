# 02 - Faster Whisper STT

## Goal

Transcribe source audio locally with faster-whisper.

## Tasks

- Add `faster-whisper` backend dependency.
- Add model/device/compute type env vars.
- Normalize output to `transcript_zh.json`.
- Save raw provider data to `transcript_zh_raw.json`.

## Acceptance Criteria

- `STT_PROVIDER=faster_whisper` produces the same normalized transcript shape as OpenAI.
- Missing dependency or audio file fails with a readable message.
