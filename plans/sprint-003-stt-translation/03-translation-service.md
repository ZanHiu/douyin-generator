# 03 - Translation Service

## Goal

Move Vietnamese translation out of the pipeline and into a provider-based service.

## Tasks

- Create `TranslationService`.
- Implement mock translation provider.
- Implement OpenAI translation provider.
- Preserve segment IDs and timestamps.
- Save translated segments to `storage/jobs/{job_id}/transcript_vi.json`.
- Retry once if OpenAI returns invalid JSON.

## Acceptance Criteria

- Mock provider creates deterministic Vietnamese transcript.
- OpenAI provider returns JSON-only translated segments when configured.
- Translation failure marks job as `failed`.

