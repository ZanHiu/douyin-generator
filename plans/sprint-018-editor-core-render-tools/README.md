# Sprint 018 - Editor Core Render Tools

## Goal

Turn the Editor from a blur-only post-process screen into a real edit render workspace for the core options that can be rendered safely in this sprint.

## Scope

- Add a generic edit render contract for video, audio, and subtitle style options.
- Implement real render support for `Trim/Speed`, `Voice volume`, `Original volume`, `Burn audio`, `Burn subtitle`, and `Caption style/position`.
- Keep `Overlay`, `Caption editor`, and `Timing editor` as placeholders for the next sprint.

## Done Criteria

- Editor sends a full render payload instead of a blur-only payload.
- Backend can produce a new edited video with trim/speed, audio mix, and subtitle style changes.
- Job History and existing Generate pipeline stay intact.
- Backend and frontend checks pass.
