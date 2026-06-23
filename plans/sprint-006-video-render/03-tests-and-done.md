# 03 - Tests And Done Criteria

## Automated Tests

- Renderer rejects missing input video.
- Renderer rejects missing voice audio.
- Renderer rejects missing subtitle file.
- Pipeline test confirms `output_vi.mp4` path is persisted.

## Manual Checks

- Run a public Douyin/TikTok URL through the app.
- Confirm job folder contains `output_vi.mp4`.
- Open or download the video.
- Confirm subtitles are burned into the video.

## Done Criteria

- `uv run pytest --basetemp D:\tmp\pytest-douyin` passes.
- A short public video produces a playable MP4.

