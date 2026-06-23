# 02 - Pipeline Integration

## Goal

Replace the TTS placeholder block with `TTSService`.

## Tasks

- Inject `TTSService` into the worker pipeline.
- Call `generate_voice(job_id, transcript_vi_path)` during `generating_tts`.
- Persist `jobs.tts_audio_path`.
- Add job log with generated voice path.
- Keep final render mocked.

## Acceptance Criteria

- Pipeline produces `voice_vi.wav`, not `voice_vi.wav.placeholder`.
- Existing UI still reaches completed state.
- Sprint 6 can consume `voice_vi.wav`.

