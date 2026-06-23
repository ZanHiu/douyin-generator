# 02 - Pipeline Integration

## Goal

Replace `output_vi.mp4.placeholder` with real render output.

## Tasks

- Inject `VideoRendererService` into the worker pipeline.
- Call renderer during `rendering_video`.
- Persist `jobs.output_video_path`.
- Keep API download endpoint unchanged.
- Add job log with output path.

## Acceptance Criteria

- UI still shows completed state.
- Download video button returns `output_vi.mp4`.
- Job folder no longer needs `output_vi.mp4.placeholder`.

