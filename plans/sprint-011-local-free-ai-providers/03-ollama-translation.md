# 03 - Ollama Translation

## Goal

Translate transcript segments locally through Ollama.

## Tasks

- Call Ollama `/api/chat`.
- Use configurable model and batch size.
- Request JSON output.
- Preserve source ids and timestamps.
- Save raw responses to `transcript_vi_raw.json`.

## Acceptance Criteria

- `TRANSLATION_PROVIDER=ollama` produces the same normalized Vietnamese transcript shape as OpenAI.
- Ollama connection/model errors fail clearly.
