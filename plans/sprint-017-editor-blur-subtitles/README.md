# Sprint 017 - Editor Blur Subtitles

## Goal

Add an edit workspace for completed jobs and support post-render blur of original subtitles without changing the Generate pipeline.

## Scope

- Add `/editor` job selector.
- Add `/editor/:jobId` edit workspace.
- Add backend endpoint to re-render a completed job with a fixed bottom blur region.
- Store edited output separately from the original generated output.

## Done Criteria

- Completed jobs can be opened in the editor from Job Detail.
- Editor can render a blurred subtitle version.
- Generate pipeline remains unchanged.
- Backend and frontend checks pass.
