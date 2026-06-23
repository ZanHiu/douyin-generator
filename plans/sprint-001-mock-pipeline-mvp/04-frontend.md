# 04 - Frontend

## Goal

Build the minimum Vue UI for submitting jobs and tracking progress.

## Pages

### Home Page

Fields:

- Video URL input.
- Voice select.
- Checkbox: burn subtitle.
- Checkbox: mix original audio.
- Generate button.

Behavior:

- Validate that URL is not empty.
- Call `POST /api/jobs`.
- Redirect to `/jobs/{job_id}` on success.
- Show readable error on failure.

### Job Page

Behavior:

- Poll `GET /api/jobs/{job_id}` every 2 seconds.
- Show status, stage, progress bar, and error message.
- Stop polling when job is `completed`, `failed`, or `cancelled`.
- Show download buttons only when URLs are available.

## Acceptance Criteria

- User can submit a URL.
- User is redirected to the progress page.
- Progress updates without page refresh.
- Failed jobs are visible and readable.
- Completed jobs show result state.

