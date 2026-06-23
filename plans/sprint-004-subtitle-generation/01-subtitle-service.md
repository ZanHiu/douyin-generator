# 01 - Subtitle Service

## Goal

Generate a valid `.srt` subtitle file from translated Vietnamese transcript segments.

## Tasks

- Create `SubtitleService`.
- Read `transcript_vi.json`.
- Validate that translated segments are a list.
- Preserve segment order by `start` time.
- Format SRT timestamps as `HH:MM:SS,mmm`.
- Use `text_vi` as subtitle text.
- Write output to `storage/jobs/{job_id}/subtitles_vi.srt`.

## Acceptance Criteria

- Valid translated transcript creates a valid SRT file.
- Invalid or missing transcript fails with readable `ProcessingError`.

