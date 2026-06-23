import json
from pathlib import Path
from typing import Any

from app.services.errors import ProcessingError
from app.services.storage_service import StorageService


class SubtitleService:
    def __init__(self, storage: StorageService | None = None) -> None:
        self.storage = storage or StorageService()

    def generate_srt(self, job_id: str, transcript_vi_path: str) -> str:
        segments = self.load_segments(transcript_vi_path)
        content = self._build_srt(segments)
        return self.storage.write_text(job_id, "subtitles_vi.srt", content)

    def load_segments(self, transcript_vi_path: str) -> list[dict[str, Any]]:
        return self._load_segments(transcript_vi_path)

    def normalize_segments(self, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not isinstance(segments, list) or not segments:
            raise ProcessingError("SUBTITLE_FAILED", "Subtitle segments must be a non-empty list.")

        normalized_segments: list[dict[str, Any]] = []
        previous_end = 0.0
        for raw in sorted(segments, key=lambda segment: float(segment.get("start", 0.0))):
            start = float(raw.get("start", 0.0))
            end = float(raw.get("end", start))
            text_vi = str(raw.get("text_vi", "")).strip()
            segment_id = int(raw.get("id", len(normalized_segments)))
            text_zh = raw.get("text_zh")

            if end < start:
                raise ProcessingError("SUBTITLE_FAILED", f"Subtitle segment {segment_id} has invalid timing.")
            if start < previous_end:
                raise ProcessingError("SUBTITLE_FAILED", f"Subtitle segment {segment_id} overlaps the previous segment.")

            normalized_segments.append(
                {
                    "id": segment_id,
                    "start": start,
                    "end": end,
                    "text_vi": text_vi,
                    "text_zh": str(text_zh) if text_zh is not None else None,
                }
            )
            previous_end = end

        return normalized_segments

    def write_segments_json(self, job_id: str, filename: str, segments: list[dict[str, Any]]) -> str:
        normalized_segments = self.normalize_segments(segments)
        return self.storage.write_json(job_id, filename, normalized_segments)

    def write_edit_segments_json(self, job_id: str, edit_id: str, filename: str, segments: list[dict[str, Any]]) -> str:
        normalized_segments = self.normalize_segments(segments)
        return self.storage.write_edit_json(job_id, edit_id, filename, normalized_segments)

    def write_srt_from_segments(self, job_id: str, filename: str, segments: list[dict[str, Any]]) -> str:
        normalized_segments = self.normalize_segments(segments)
        content = self._build_srt(normalized_segments)
        return self.storage.write_text(job_id, filename, content)

    def write_edit_srt_from_segments(self, job_id: str, edit_id: str, filename: str, segments: list[dict[str, Any]]) -> str:
        normalized_segments = self.normalize_segments(segments)
        content = self._build_srt(normalized_segments)
        return self.storage.write_edit_text(job_id, edit_id, filename, content)

    def _load_segments(self, transcript_vi_path: str) -> list[dict[str, Any]]:
        path = self.storage.resolve_path(transcript_vi_path)
        if not path.exists():
            raise ProcessingError("SUBTITLE_FAILED", "Missing Vietnamese transcript.")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProcessingError("SUBTITLE_FAILED", "Vietnamese transcript is not valid JSON.") from exc

        if not isinstance(data, list):
            raise ProcessingError("SUBTITLE_FAILED", "Vietnamese transcript must be a segment list.")
        return data

    def _build_srt(self, segments: list[dict[str, Any]]) -> str:
        sorted_segments = sorted(segments, key=lambda segment: float(segment.get("start", 0.0)))
        blocks = []
        for index, segment in enumerate(sorted_segments, start=1):
            text = str(segment.get("text_vi", "")).strip()
            if not text:
                continue

            start = float(segment.get("start", 0.0))
            end = float(segment.get("end", start))
            if end < start:
                end = start

            blocks.append(
                "\n".join(
                    [
                        str(index),
                        f"{self.format_timestamp(start)} --> {self.format_timestamp(end)}",
                        text,
                    ]
                )
            )

        if not blocks:
            raise ProcessingError("SUBTITLE_FAILED", "No Vietnamese segments available for subtitle generation.")

        return "\n\n".join(blocks) + "\n"

    @staticmethod
    def format_timestamp(seconds: float) -> str:
        if seconds < 0:
            seconds = 0
        total_milliseconds = int(round(seconds * 1000))
        milliseconds = total_milliseconds % 1000
        total_seconds = total_milliseconds // 1000
        secs = total_seconds % 60
        total_minutes = total_seconds // 60
        minutes = total_minutes % 60
        hours = total_minutes // 60
        return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"
