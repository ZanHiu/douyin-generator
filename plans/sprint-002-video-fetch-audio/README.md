# Sprint 002 - Video Fetch And Audio Extraction

## Summary

Replace the first two mock stages with real media processing:

```text
fetching_video -> yt-dlp download
extracting_audio -> FFmpeg WAV extraction
```

The later stages remain mocked in this sprint.

## Phase Files

```text
01-url-validation-and-config.md
02-video-fetch.md
03-audio-extraction.md
04-pipeline-integration.md
05-tests-and-done.md
```

## Done Criteria

- Existing mock pipeline tests still pass by injecting fake media services.
- A real public TikTok/Douyin URL can progress through real fetch/audio extraction and mocked later stages.
- Failure does not crash backend or worker; the job becomes `failed`.
