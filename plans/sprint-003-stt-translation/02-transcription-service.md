# 02 - Transcription Service

## Goal

Move transcript generation out of the pipeline and into a provider-based service.

## Tasks

- Create `TranscriptionService`.
- Implement mock transcription provider.
- Implement OpenAI transcription provider.
- Save normalized transcript to `storage/jobs/{job_id}/transcript_zh.json`.
- Save raw OpenAI output to `storage/jobs/{job_id}/transcript_zh_raw.json` when using OpenAI.
- Preserve segment IDs, start times, end times, and Chinese text.

## Acceptance Criteria

- Mock provider produces deterministic Chinese transcript.
- OpenAI provider can transcribe `audio.wav` when configured.
- Transcription failure marks job as `failed`.

