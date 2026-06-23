# 02 - Voice Polish

## Goal

Create a render-ready voice track.

## Tasks

- Increase voice loudness with `VOICE_VOLUME_MULTIPLIER`.
- Pad silence when TTS ends before video ends.
- Trim audio if TTS extends beyond source video duration.
- Write `voice_vi_render.wav`.

## Acceptance Criteria

- `voice_vi_render.wav` duration matches source video duration.
