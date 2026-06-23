# 05 - Tests And Done Criteria

## Automated Tests

- Missing FPT API key raises `ProcessingError`.
- FPT async URL extraction supports `async`, `async_url`, and `url`.
- Segment audio alignment command is testable without calling provider.
- Existing pipeline tests pass with mock TTS.

## Manual Checks

- Configure FPT AI env vars.
- Run a short public video.
- Confirm `tts/*.mp3`, `tts/*.wav`, and `voice_vi.wav` exist.
- Confirm rendered output video has audible Vietnamese voice.

## Done Criteria

- `uv run pytest --basetemp D:\tmp\pytest-douyin` passes.
- A configured FPT AI account can generate real voice audio.

