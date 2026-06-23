import subprocess
from pathlib import Path

from app.core.config import settings
from app.services.errors import ProcessingError
from app.services.storage_service import StorageService


class AudioExtractorService:
    def __init__(self, storage: StorageService | None = None) -> None:
        self.storage = storage or StorageService()

    def extract(self, job_id: str, input_video_path: str) -> str:
        input_path = Path(input_video_path)
        if not input_path.exists():
            raise ProcessingError("AUDIO_EXTRACTION_FAILED", "Missing input video file.")

        output_path = self.storage.job_dir(job_id) / "audio.wav"
        args = [
            settings.ffmpeg_bin,
            "-y",
            "-i",
            str(input_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(output_path),
        ]

        try:
            subprocess.run(
                args,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as exc:
            raise ProcessingError(
                "MISSING_BINARY",
                f"Missing tool: {settings.ffmpeg_bin}. Check PATH or FFMPEG_BIN.",
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            message = f"Could not extract audio with FFmpeg. {detail}" if detail else "Could not extract audio with FFmpeg."
            raise ProcessingError("AUDIO_EXTRACTION_FAILED", message) from exc

        if not output_path.exists():
            raise ProcessingError("AUDIO_EXTRACTION_FAILED", "FFmpeg did not create the audio file.")

        return str(output_path)
