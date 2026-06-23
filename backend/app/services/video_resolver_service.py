import json
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import settings
from app.services.errors import ProcessingError
from app.services.storage_service import StorageService


class VideoResolverService:
    def __init__(self, storage: StorageService | None = None) -> None:
        self.storage = storage or StorageService()

    def fetch(self, job_id: str, source_url: str) -> tuple[str, str]:
        self._validate_supported_url(source_url)
        job_dir = self.storage.job_dir(job_id)

        metadata = self._read_metadata(source_url)
        self._validate_duration(metadata.get("duration"))

        output_template = str(job_dir / "input.%(ext)s")
        self._run(
            [
                settings.ytdlp_bin,
                "--no-playlist",
                "--merge-output-format",
                "mp4",
                "-f",
                "bv*+ba/b",
                "-o",
                output_template,
                source_url,
            ],
            "Could not download video from this URL.",
        )

        input_path = self._find_downloaded_video(job_dir)
        self._validate_file_size(input_path)

        probe_metadata = self._probe_video(input_path)
        metadata.update(probe_metadata)
        metadata["source_url"] = source_url
        metadata["platform"] = self.detect_platform(source_url)
        metadata["downloaded_path"] = str(input_path)

        self._validate_duration(metadata.get("duration_seconds"))
        metadata_path = self.storage.write_json(job_id, "metadata.json", metadata)
        return str(input_path), metadata_path

    def _read_metadata(self, source_url: str) -> dict:
        result = self._run(
            [
                settings.ytdlp_bin,
                "--dump-json",
                "--no-playlist",
                "--skip-download",
                source_url,
            ],
            "Could not read video metadata.",
        )
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ProcessingError("VIDEO_FETCH_FAILED", "Invalid video metadata.") from exc

    def _probe_video(self, input_path: Path) -> dict:
        result = self._run(
            [
                settings.ffprobe_bin,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(input_path),
            ],
            "Could not inspect downloaded video.",
        )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ProcessingError("VIDEO_FETCH_FAILED", "Invalid downloaded video metadata.") from exc

        video_stream = next(
            (stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"),
            {},
        )
        duration = data.get("format", {}).get("duration")
        return {
            "duration_seconds": float(duration) if duration else None,
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "file_size_bytes": input_path.stat().st_size,
        }

    def _find_downloaded_video(self, job_dir: Path) -> Path:
        candidates = sorted(job_dir.glob("input.*"))
        video_candidates = [path for path in candidates if path.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}]
        if not video_candidates:
            raise ProcessingError("VIDEO_FETCH_FAILED", "No video file was found after download.")
        return video_candidates[0]

    def _validate_supported_url(self, source_url: str) -> None:
        parsed = urlparse(source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ProcessingError("INVALID_URL", "Invalid URL.")
        if self.detect_platform(source_url) is None:
            raise ProcessingError("UNSUPPORTED_PLATFORM", "Only Douyin and TikTok URLs are supported in this MVP.")

    def _validate_duration(self, duration: object) -> None:
        if duration is None:
            return
        try:
            duration_seconds = float(duration)
        except (TypeError, ValueError):
            return
        if duration_seconds > settings.max_video_duration_seconds:
            raise ProcessingError(
                "VIDEO_TOO_LONG",
                f"Video is too long. This MVP supports up to {settings.max_video_duration_seconds} seconds.",
            )

    def _validate_file_size(self, input_path: Path) -> None:
        max_bytes = settings.max_video_file_mb * 1024 * 1024
        if input_path.stat().st_size > max_bytes:
            raise ProcessingError(
                "VIDEO_TOO_LARGE",
                f"Video is too large. This MVP supports up to {settings.max_video_file_mb} MB.",
            )

    def _run(self, args: list[str], user_message: str) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
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
                f"Missing tool: {args[0]}. Check PATH or environment variables.",
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            message = f"{user_message} {detail}" if detail else user_message
            raise ProcessingError("VIDEO_FETCH_FAILED", message) from exc

    @staticmethod
    def detect_platform(source_url: str) -> str | None:
        hostname = (urlparse(source_url).hostname or "").lower()
        if hostname == "douyin.com" or hostname.endswith(".douyin.com") or hostname.endswith(".iesdouyin.com"):
            return "douyin"
        if (
            hostname == "tiktok.com"
            or hostname.endswith(".tiktok.com")
            or hostname in {"vm.tiktok.com", "vt.tiktok.com"}
        ):
            return "tiktok"
        return None
