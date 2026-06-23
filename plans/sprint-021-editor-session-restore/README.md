# Sprint 021 - Editor Session Restore

## Goal

Restore a previously saved editor render back into the editor workspace so reopening an edit from history resumes the exact saved configuration instead of starting from a blank editor state.

## Scope

- Add backend read API for a saved edit configuration.
- Extend editor frontend state loading to hydrate controls from saved edit config.
- Pass `edit` query param when reopening an edit from editor history.
- Reuse the saved edited video as the initial preview when reopening that edit.

## Done Criteria

- `Edit history -> Reopen` opens `/editor/{jobId}?edit={editId}`.
- Editor controls restore saved values from that edit.
- Preview starts with the saved edited output.
- Backend and frontend checks pass.
