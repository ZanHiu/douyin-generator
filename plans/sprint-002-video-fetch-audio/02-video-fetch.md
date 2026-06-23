# 02 - Video Fetch

## Goal

Replace the `fetching_video` mock stage with real video download.

## Tasks

- Create `VideoResolverService`.
- Use `yt-dlp --dump-json --skip-download` to read source metadata.
- Enforce max duration before download when duration is available.
- Use `yt-dlp` to download the source video to `storage/jobs/{job_id}/input.*`.
- Prefer MP4 merge output when possible.
- Use `ffprobe` to read downloaded file metadata.
- Save metadata to `storage/jobs/{job_id}/metadata.json`.
- Persist `jobs.input_video_path`.

## Failure Cases

- Missing `yt-dlp`.
- Missing `ffprobe`.
- Unsupported URL.
- Private/unavailable video.
- Download failure.
- Video over duration limit.
- Video over file size limit.

## Acceptance Criteria

- A public supported URL creates an `input.*` file.
- `metadata.json` contains source URL, platform, duration, width, height, and file size when available.
- Failure marks the job as `failed` with a readable message.

