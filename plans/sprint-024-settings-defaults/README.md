# Sprint 024 - Settings Defaults

Goal: turn the Settings route into a real defaults workspace and use those saved defaults to prefill new jobs and editor baselines.

Scope:

- Add per-user settings storage.
- Add authenticated settings APIs.
- Replace the Settings placeholder with a real form.
- Prefill Generate with saved defaults.
- Snapshot render defaults onto each new job so later edits stay stable.

Expected outcome:

- The operator can save preferred voice, audio mix, and subtitle/render defaults.
- Generate opens with those defaults already applied.
- New jobs keep a stable render baseline even if Settings change later.
