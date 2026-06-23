# 02 - Segment Audio Generation

## Goal

Generate one TTS audio file per Vietnamese transcript segment.

## Tasks

- Read `text_vi` from `transcript_vi.json`.
- Call FPT AI TTS endpoint per segment.
- Support async response URL from provider.
- Download generated audio to `tts/{index}.mp3`.
- Convert each generated file to mono WAV `tts/{index}.wav`.

## Acceptance Criteria

- Each non-empty Vietnamese segment produces an audio artifact.
- Provider/download/convert failures mark the job as failed.

