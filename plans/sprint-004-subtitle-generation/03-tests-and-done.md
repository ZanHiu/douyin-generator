# 03 - Tests And Done Criteria

## Automated Tests

- Timestamp formatter handles seconds, minutes, hours, and milliseconds.
- Valid `transcript_vi.json` generates expected SRT content.
- Missing transcript raises `ProcessingError`.
- Pipeline test confirms `subtitles_vi.srt` is generated from service output.

## Manual Checks

- Run a public Douyin/TikTok URL through the app.
- Confirm job completes.
- Open `storage/jobs/{job_id}/subtitles_vi.srt`.
- Confirm SRT numbering, timestamps, and Vietnamese text are present.

## Done Criteria

- `uv run pytest --basetemp D:\tmp\pytest-douyin` passes.
- Subtitle download button returns generated `.srt`.

