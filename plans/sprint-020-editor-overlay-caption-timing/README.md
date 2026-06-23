# Sprint 020 - Editor Overlay Caption Timing

## Goal

Implement the remaining editor tools that still existed as placeholders so the editor can render meaningful post-processing changes across video and subtitles.

## Scope

- Add basic text overlay render support.
- Add caption text editing from Vietnamese transcript segments.
- Add subtitle timing editing with per-segment start/end controls.
- Expose editor-state API for transcript segments.

## Done Criteria

- `Video > Overlay` renders a visible text overlay.
- `Captions > Caption editor` updates subtitle text in the rendered output.
- `Captions > Timing editor` updates subtitle timing in the rendered output.
- Backend and frontend checks pass.
