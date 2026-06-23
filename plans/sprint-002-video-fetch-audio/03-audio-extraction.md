# 03 - Audio Extraction

## Goal

Replace the `extracting_audio` mock stage with real FFmpeg audio extraction.

## Tasks

- Create `AudioExtractorService`.
- Use FFmpeg to extract mono 16k WAV:

```text
ffmpeg -y -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav
```

- Write output to `storage/jobs/{job_id}/audio.wav`.
- Persist `jobs.audio_path`.

## Failure Cases

- Missing `ffmpeg`.
- Input video file missing.
- FFmpeg exits non-zero.
- FFmpeg does not create `audio.wav`.

## Acceptance Criteria

- A successfully downloaded video creates `audio.wav`.
- Failure marks the job as `failed` with a readable message.

