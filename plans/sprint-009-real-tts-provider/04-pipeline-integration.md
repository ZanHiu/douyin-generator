# 04 - Pipeline Integration

## Goal

Wire provider-aware TTS into the existing worker pipeline.

## Tasks

- Pass `job.voice_id` into `TTSService.generate_voice`.
- Use `FPT_AI_VOICE_ID` when job voice is not provider-compatible.
- Keep output path `voice_vi.wav`.
- Keep final render unchanged.

## Acceptance Criteria

- `TTS_PROVIDER=mock` still works.
- `TTS_PROVIDER=fpt_ai` uses provider audio.

