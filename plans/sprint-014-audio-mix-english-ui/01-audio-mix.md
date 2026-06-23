# 01 - Audio Mix

## Tasks

- Add original-audio and mix-voice volume settings.
- Pass extracted original audio into the renderer.
- Extend `VideoRendererService.render(...)` with `mix_original_audio`.
- Build separate FFmpeg args for:
  - voice-only output
  - voice + original-background mix
- Keep output audio track marked as Vietnamese/default.

## Notes

Original audio should be quiet enough to preserve ambience without competing with TTS.
