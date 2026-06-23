from pathlib import Path
from typing import Any
from collections.abc import Callable

from app.core.config import settings
from app.services.errors import ProcessingError
from app.services.storage_service import StorageService


class TranscriptionService:
    def __init__(self, storage: StorageService | None = None) -> None:
        self.storage = storage or StorageService()

    def transcribe(
        self,
        job_id: str,
        audio_path: str,
        *,
        cancel_checker: Callable[[], bool] | None = None,
        progress_logger: Callable[[str], None] | None = None,
    ) -> str:
        provider = settings.stt_provider.lower()
        if provider == "mock":
            return self._mock_transcribe(job_id)
        if provider == "openai":
            return self._openai_transcribe(
                job_id,
                audio_path,
                cancel_checker=cancel_checker,
            )
        if provider == "faster_whisper":
            return self._faster_whisper_transcribe(
                job_id,
                audio_path,
                cancel_checker=cancel_checker,
                progress_logger=progress_logger,
            )
        raise ProcessingError("TRANSCRIPTION_FAILED", f"Unsupported STT provider: {provider}")

    def _mock_transcribe(self, job_id: str) -> str:
        return self.storage.write_json(
            job_id,
            "transcript_zh.json",
            {
                "language": "zh",
                "segments": [
                    {
                        "id": 0,
                        "start": 0.0,
                        "end": 2.4,
                        "text": "大家好，今天我们来做一道菜。",
                    },
                    {
                        "id": 1,
                        "start": 2.5,
                        "end": 5.0,
                        "text": "这个方法很简单。",
                    },
                ],
            },
        )

    def _openai_transcribe(
        self,
        job_id: str,
        audio_path: str,
        *,
        cancel_checker: Callable[[], bool] | None = None,
    ) -> str:
        if not settings.openai_api_key:
            raise ProcessingError("TRANSCRIPTION_FAILED", "OPENAI_API_KEY is not configured.")

        input_path = self.storage.resolve_path(audio_path)
        if not input_path.exists():
            raise ProcessingError("TRANSCRIPTION_FAILED", "Missing audio file for transcription.")
        self._raise_if_cancelled(cancel_checker)

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.openai_request_timeout_seconds,
            )
            with input_path.open("rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model=settings.transcription_model,
                    file=audio_file,
                    language="zh",
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )
        except Exception as exc:
            raise ProcessingError("TRANSCRIPTION_FAILED", f"Transcription failed: {exc}") from exc
        self._raise_if_cancelled(cancel_checker)

        raw = self._to_plain_data(response)
        self.storage.write_json(job_id, "transcript_zh_raw.json", raw)

        normalized_segments = self._normalize_openai_segments(raw)

        if not normalized_segments:
            raise ProcessingError("TRANSCRIPTION_FAILED", "STT provider returned no transcript segments.")

        return self.storage.write_json(
            job_id,
            "transcript_zh.json",
            {
                "language": raw.get("language", "zh"),
                "segments": normalized_segments,
            },
        )

    def _faster_whisper_transcribe(
        self,
        job_id: str,
        audio_path: str,
        *,
        cancel_checker: Callable[[], bool] | None = None,
        progress_logger: Callable[[str], None] | None = None,
    ) -> str:
        input_path = self.storage.resolve_path(audio_path)
        if not input_path.exists():
            raise ProcessingError("TRANSCRIPTION_FAILED", "Missing audio file for transcription.")
        self._raise_if_cancelled(cancel_checker)

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ProcessingError(
                "TRANSCRIPTION_FAILED",
                "faster-whisper is not installed. Run `uv sync` in the backend folder.",
            ) from exc

        try:
            if progress_logger is not None:
                progress_logger("Loading faster-whisper model")
            model = WhisperModel(
                settings.whisper_model,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
            )
            self._raise_if_cancelled(cancel_checker)
            if progress_logger is not None:
                progress_logger("Running faster-whisper transcription")
            segments_iter, info = model.transcribe(
                str(input_path),
                language="zh",
                vad_filter=True,
            )
            raw_segments = []
            for index, segment in enumerate(segments_iter):
                self._raise_if_cancelled(cancel_checker)
                raw_segments.append(
                    {
                        "id": index,
                        "start": float(segment.start),
                        "end": float(segment.end),
                        "text": str(segment.text).strip(),
                    }
                )
        except Exception as exc:
            raise ProcessingError("TRANSCRIPTION_FAILED", f"faster-whisper failed: {exc}") from exc

        raw = {
            "provider": "faster_whisper",
            "model": settings.whisper_model,
            "language": getattr(info, "language", "zh"),
            "language_probability": getattr(info, "language_probability", None),
            "segments": raw_segments,
        }
        self.storage.write_json(job_id, "transcript_zh_raw.json", raw)

        normalized_segments = self._normalize_openai_segments(raw)
        if not normalized_segments:
            raise ProcessingError("TRANSCRIPTION_FAILED", "faster-whisper returned no transcript segments.")

        return self.storage.write_json(
            job_id,
            "transcript_zh.json",
            {
                "language": raw.get("language", "zh"),
                "segments": normalized_segments,
            },
        )

    @staticmethod
    def _normalize_openai_segments(raw: dict[str, Any]) -> list[dict[str, Any]]:
        segments = raw.get("segments") or []
        normalized_segments = []
        for index, segment in enumerate(segments):
            text = str(segment.get("text", "")).strip()
            if not text:
                continue
            start = max(float(segment.get("start", 0.0)), 0.0)
            end = max(float(segment.get("end", start)), start)
            normalized_segments.append(
                {
                    "id": int(segment.get("id", index)),
                    "start": start,
                    "end": end,
                    "text": text,
                }
            )

        if not normalized_segments and raw.get("text"):
            normalized_segments.append(
                {
                    "id": 0,
                    "start": 0.0,
                    "end": 0.0,
                    "text": str(raw["text"]).strip(),
                }
            )
        return normalized_segments

    @staticmethod
    def _to_plain_data(response: Any) -> dict[str, Any]:
        if isinstance(response, dict):
            return response
        if hasattr(response, "model_dump"):
            return response.model_dump()
        if hasattr(response, "dict"):
            return response.dict()
        raise ProcessingError("TRANSCRIPTION_FAILED", "STT provider returned an unsupported response.")

    @staticmethod
    def _raise_if_cancelled(cancel_checker: Callable[[], bool] | None) -> None:
        if cancel_checker is not None and cancel_checker():
            raise ProcessingError("JOB_CANCELLED", "Job cancelled")
