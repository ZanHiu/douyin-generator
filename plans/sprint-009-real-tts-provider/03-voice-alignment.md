# 03 - Voice Alignment

## Goal

Build `voice_vi.wav` by placing each generated segment at the transcript start timestamp.

## Tasks

- Use FFmpeg `adelay` and `amix` to align segment WAV files.
- Output mono WAV.
- Keep existing mock silent WAV alignment for local testing.

## Acceptance Criteria

- `voice_vi.wav` contains all generated segment audio aligned by timestamp.
- Existing mock TTS tests still pass.

