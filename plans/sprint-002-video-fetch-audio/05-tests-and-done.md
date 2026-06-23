# 05 - Tests And Done Criteria

## Automated Tests

- URL validation accepts Douyin/TikTok.
- URL validation rejects unsupported hosts.
- Platform detection identifies Douyin.
- Platform detection identifies TikTok.
- Mock pipeline tests still pass by injecting fake video/audio services.
- Mock pipeline persists `input_video_path` and `audio_path`.

## Manual Checks

- Verify installed tools:

```powershell
yt-dlp --version
ffmpeg -version
ffprobe -version
```

- Restart backend API and Celery worker after `.env` changes.
- Submit a real public TikTok/Douyin URL from the frontend.
- Confirm the job folder contains:

```text
input.mp4
audio.wav
metadata.json
```

## Done Criteria

- `uv run pytest --basetemp D:\tmp\pytest-douyin` passes.
- Real media fetch and audio extraction work for at least one public short video.
- Later mock stages still complete the job.

