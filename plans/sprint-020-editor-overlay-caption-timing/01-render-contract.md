# Render Contract

- Extend editor render payload with:
  - `subtitle_segments`
  - `overlay_enabled`
  - `overlay_text`
  - `overlay_position`
  - `overlay_font_size`
  - `overlay_text_color`
- Add `GET /api/jobs/{job_id}/editor-state` to load transcript segments for editing.
