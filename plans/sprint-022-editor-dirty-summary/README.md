# Sprint 022 - Editor Dirty Summary

## Goal

Make the editor behave like a real workspace:

- `Render` is only enabled when the user has pending changes.
- The editor can show what has changed before render.
- Group/tool badges make pending edits visible at a glance.
- Editor controls use a small reusable field system instead of ad hoc markup.

## Scope

### 1. Dirty state and baseline tracking

- Load a normalized baseline config when opening `/editor/:jobId`.
- If the user opens from Job Detail, baseline = generated final render config.
- If the user opens from Edit History, baseline = saved edit config.
- Compare current editor state against baseline to determine dirty state.

### 2. Pending change summary

- Compute pending changes by group:
  - `Video`
  - `Audio`
  - `Captions`
- Compute pending changes by option tool:
  - `Trim/Speed`
  - `Blur/Mask`
  - `Overlay`
  - `Style/Position`
  - `Subtitle editor`
- Show:
  - badge count on toolbar group buttons
  - badge count on option tabs
  - compact pending summary near render actions

### 3. Render gating

- Disable `Render` when there are no pending changes.
- Keep `Download` disabled until an edited output exists.
- After successful render:
  - update preview URL
  - reset baseline to current config
  - clear dirty state

### 4. Editor field primitives

- Introduce a minimal reusable UI layer for editor controls:
  - generic field wrapper
  - toggle field
- Refactor trim / blur / overlay / audio / caption style controls to use the same structure.
- Keep subtitle segment editor boxed because repeated rows benefit from stronger separation.

## Out of scope

- Draft persistence / autosave
- Live preview without render
- New edit tools
- DB schema change for richer edit audit metadata

## Acceptance criteria

- Opening editor with no changes shows disabled `Render`.
- Editing one control enables `Render`.
- Pending summary reflects changed groups/tools.
- Reopening a saved edit starts from that saved config with clean dirty state.
- Frontend type-check and build pass.
