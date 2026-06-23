# 03 - Tests And Done Criteria

## Automated Tests

- Mock TTS creates per-segment WAV files.
- Mock TTS creates aligned `voice_vi.wav`.
- Generated WAV has expected sample rate, channel count, and duration.
- Missing transcript raises `ProcessingError`.
- Pipeline test confirms `voice_vi.wav` exists.

## Manual Checks

- Run a public Douyin/TikTok URL through the app.
- Confirm job completes.
- Confirm job folder contains:

```text
tts/000.wav
tts/001.wav
voice_vi.wav
```

## Done Criteria

- `uv run pytest --basetemp D:\tmp\pytest-douyin` passes.
- `voice_vi.wav` is present for completed jobs.

