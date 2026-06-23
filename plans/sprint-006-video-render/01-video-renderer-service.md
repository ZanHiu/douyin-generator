# 01 - Video Renderer Service

## Goal

Generate a real `output_vi.mp4` using FFmpeg.

## Tasks

- Create `VideoRendererService`.
- Validate required input files:
  - `input_video_path`
  - `tts_audio_path`
  - `subtitle_path`
- Render option A for MVP:
  - keep source video stream
  - replace audio with `voice_vi.wav`
  - burn `subtitles_vi.srt`
  - output `output_vi.mp4`
- Escape subtitle path for FFmpeg filter usage on Windows.

## Acceptance Criteria

- Completed jobs create `output_vi.mp4`.
- Missing input files fail with readable `ProcessingError`.
- FFmpeg failures mark job as `failed`.

