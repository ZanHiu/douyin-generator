# 02 - Pipeline Integration

## Goal

Replace the hardcoded `generating_subtitles` block with `SubtitleService`.

## Tasks

- Inject `SubtitleService` into the worker pipeline.
- Call `generate_srt(job_id, transcript_vi_path)` during `generating_subtitles`.
- Persist `jobs.subtitle_path`.
- Add job log with generated subtitle path.
- Keep TTS and final render stages mocked.

## Acceptance Criteria

- Pipeline uses translated transcript to create subtitles.
- UI still shows completed state.
- Download subtitle endpoint returns the generated SRT file.

