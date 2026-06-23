# 01 - TTS Service

## Goal

Generate a real WAV file for Vietnamese narration output.

## Tasks

- Create `TTSService`.
- Read translated segments from `transcript_vi.json`.
- Implement mock provider that creates:
  - per-segment silent WAV files under `tts/`
  - aligned `voice_vi.wav`
- Use mono PCM 16-bit WAV.
- Use `TTS_SAMPLE_RATE`, default `16000`.
- Fail clearly for missing/invalid transcript or unsupported provider.

## Acceptance Criteria

- `voice_vi.wav` is a valid WAV file.
- The WAV duration covers the last translated segment end timestamp.
- Per-segment files are created in `storage/jobs/{job_id}/tts/`.

