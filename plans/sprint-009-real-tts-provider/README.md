# Sprint 009 - Real TTS Provider

## Summary

Add a real Vietnamese TTS provider adapter while keeping `mock` as the default.

The first real provider is FPT AI. It generates per-segment audio, converts each segment to WAV, and aligns the final `voice_vi.wav` by transcript timestamps.

## Phase Files

```text
01-fpt-ai-config.md
02-segment-audio-generation.md
03-voice-alignment.md
04-pipeline-integration.md
05-tests-and-done.md
```

