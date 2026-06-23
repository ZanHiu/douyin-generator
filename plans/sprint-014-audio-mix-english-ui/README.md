# Sprint 014 - Audio Mix & English UI

## Goal

Make the final output controls match the product behavior and clean the user-facing UI language.

## Scope

- Implement `mix_original_audio` for final video rendering.
- Keep Vietnamese voice as the primary output audio.
- Optionally mix source/original audio under the Vietnamese voice at a low volume.
- Convert frontend visible text to English.
- Keep backend changes focused on renderer/pipeline paths touched by this sprint.

## Done Criteria

- Final video contains Vietnamese voice when `mix_original_audio=false`.
- Final video contains Vietnamese voice plus quiet original audio when `mix_original_audio=true`.
- Frontend pages/components no longer mix Vietnamese and English labels.
- Backend tests cover both render modes.
- Frontend typecheck/build and backend tests pass.
