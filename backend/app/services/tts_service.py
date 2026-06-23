import json
import subprocess
import time
import wave
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.services.errors import ProcessingError
from app.services.storage_service import StorageService


class TTSService:
    def __init__(self, storage: StorageService | None = None) -> None:
        self.storage = storage or StorageService()

    def generate_voice(self, job_id: str, transcript_vi_path: str, voice_id: str | None = None) -> str:
        provider = settings.tts_provider.lower()
        segments = self._load_segments(transcript_vi_path)
        if provider == "mock":
            return self._mock_generate_voice(job_id, segments)
        if provider == "fpt_ai":
            return self._fpt_ai_generate_voice(job_id, segments, voice_id)
        raise ProcessingError("TTS_FAILED", f"Unsupported TTS provider: {provider}")

    def _load_segments(self, transcript_vi_path: str) -> list[dict[str, Any]]:
        path = self.storage.resolve_path(transcript_vi_path)
        if not path.exists():
            raise ProcessingError("TTS_FAILED", "Missing Vietnamese transcript.")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProcessingError("TTS_FAILED", "Vietnamese transcript is not valid JSON.") from exc

        if not isinstance(data, list):
            raise ProcessingError("TTS_FAILED", "Vietnamese transcript must be a segment list.")

        segments = [segment for segment in data if str(segment.get("text_vi", "")).strip()]
        if not segments:
            raise ProcessingError("TTS_FAILED", "No Vietnamese segments available for voice generation.")
        return segments

    def _mock_generate_voice(self, job_id: str, segments: list[dict[str, Any]]) -> str:
        job_dir = self.storage.job_dir(job_id)
        tts_dir = job_dir / "tts"
        tts_dir.mkdir(parents=True, exist_ok=True)

        sample_rate = settings.tts_sample_rate
        max_end = 0.0
        normalized_segments = []
        for index, segment in enumerate(segments):
            start = max(float(segment.get("start", 0.0)), 0.0)
            end = max(float(segment.get("end", start)), start)
            max_end = max(max_end, end)
            segment_path = tts_dir / f"{index:03}.wav"
            self._write_silence(segment_path, max(end - start, 0.1), sample_rate)
            normalized_segments.append((start, end, segment_path))

        total_duration = max(max_end, 0.1)
        output_path = job_dir / "voice_vi.wav"
        total_frames = max(int(round(total_duration * sample_rate)), 1)
        audio = bytearray(total_frames * 2)

        # Mock TTS is silent, but the loop preserves the future overlay structure.
        for start, end, _segment_path in normalized_segments:
            start_frame = int(round(start * sample_rate))
            end_frame = min(int(round(end * sample_rate)), total_frames)
            if end_frame > start_frame:
                continue

        self._write_pcm(output_path, bytes(audio), sample_rate)
        return str(output_path)

    def _fpt_ai_generate_voice(
        self,
        job_id: str,
        segments: list[dict[str, Any]],
        voice_id: str | None,
    ) -> str:
        if not settings.fpt_ai_api_key:
            raise ProcessingError("TTS_FAILED", "FPT_AI_API_KEY is not configured.")

        job_dir = self.storage.job_dir(job_id)
        tts_dir = job_dir / "tts"
        tts_dir.mkdir(parents=True, exist_ok=True)

        segment_wavs = []
        for index, segment in enumerate(segments):
            text = self._normalize_fpt_text(str(segment.get("text_vi", "")).strip())
            if not text:
                continue

            source_extension = self._resolve_fpt_audio_extension()
            raw_path = tts_dir / f"{index:03}{source_extension}"
            wav_path = tts_dir / f"{index:03}.wav"
            self._request_fpt_ai_segment(text, raw_path, self._resolve_fpt_voice_id(voice_id))
            self._convert_to_wav(raw_path, wav_path)
            segment_wavs.append((float(segment.get("start", 0.0)), wav_path))

        if not segment_wavs:
            raise ProcessingError("TTS_FAILED", "FPT AI did not generate any audio segments.")

        output_path = job_dir / "voice_vi.wav"
        self._align_segment_wavs(segment_wavs, output_path)
        return str(output_path)

    def _request_fpt_ai_segment(self, text: str, output_path: Path, voice_id: str) -> None:
        headers = {
            "api-key": settings.fpt_ai_api_key or "",
            "api_key": settings.fpt_ai_api_key or "",
            "voice": voice_id,
            "speed": settings.fpt_ai_speed,
            "format": settings.fpt_ai_format,
            "Cache-Control": "no-cache",
        }
        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(
                    settings.fpt_ai_tts_url,
                    headers=headers,
                    content=text.encode("utf-8"),
                )
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    detail = response.text.strip()
                    message = f"FPT AI TTS request failed: {exc}"
                    if detail:
                        message += f" Response: {detail}"
                    raise ProcessingError("TTS_FAILED", message) from exc
                audio_response = (
                    response.content
                    if response.headers.get("content-type", "").startswith("audio/")
                    else self._download_fpt_audio(client, self._extract_fpt_audio_url(response))
                )
        except httpx.HTTPError as exc:
            raise ProcessingError("TTS_FAILED", f"FPT AI TTS request failed: {exc}") from exc

        output_path.write_bytes(audio_response)

    @staticmethod
    def _normalize_fpt_text(text: str) -> str:
        normalized = " ".join(text.split())
        if not normalized:
            return ""
        if len(normalized) < 3:
            return f"{normalized}..."
        return normalized

    def _extract_fpt_audio_url(self, response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError as exc:
            raise ProcessingError("TTS_FAILED", "FPT AI response is not valid JSON.") from exc

        if isinstance(data, dict):
            error_code = str(data.get("error", "0"))
            if error_code != "0":
                message = data.get("message") or f"FPT AI error: {error_code}"
                raise ProcessingError("TTS_FAILED", str(message))

        audio_url = ""
        if isinstance(data, dict):
            audio_url = str(data.get("async") or data.get("async_url") or data.get("url") or "")

        if not audio_url:
            raise ProcessingError("TTS_FAILED", "FPT AI response has no audio URL.")
        return audio_url

    @staticmethod
    def _resolve_fpt_voice_id(voice_id: str | None) -> str:
        generic_voice_ids = {"vi_female_01", "vi_male_01", "", None}
        if voice_id in generic_voice_ids:
            return settings.fpt_ai_voice_id
        return str(voice_id)

    @staticmethod
    def _resolve_fpt_audio_extension() -> str:
        audio_format = settings.fpt_ai_format.lower().strip(".")
        if audio_format not in {"mp3", "wav"}:
            raise ProcessingError("TTS_FAILED", f"Unsupported FPT_AI_FORMAT: {settings.fpt_ai_format}")
        return f".source.{audio_format}" if audio_format == "wav" else ".mp3"

    def _download_fpt_audio(self, client: httpx.Client, audio_url: str) -> bytes:
        last_status = None
        for _attempt in range(settings.tts_poll_attempts):
            response = client.get(audio_url)
            last_status = response.status_code
            if response.status_code == 200 and response.content:
                return response.content
            time.sleep(settings.tts_poll_interval_seconds)
        raise ProcessingError("TTS_FAILED", f"Could not download audio from FPT AI. Last HTTP status: {last_status}")

    def _convert_to_wav(self, input_path: Path, output_path: Path) -> None:
        args = [
            settings.ffmpeg_bin,
            "-y",
            "-i",
            str(input_path),
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(settings.tts_sample_rate),
            "-ac",
            "1",
            str(output_path),
        ]
        self._run_ffmpeg(args, "Could not convert TTS audio to WAV.")

    def _align_segment_wavs(self, segment_wavs: list[tuple[float, Path]], output_path: Path) -> None:
        args = [settings.ffmpeg_bin, "-y"]
        for _start, path in segment_wavs:
            args.extend(["-i", str(path)])

        filters = []
        labels = []
        for index, (start, _path) in enumerate(segment_wavs):
            label = f"a{index}"
            delay_ms = max(int(round(start * 1000)), 0)
            filters.append(f"[{index}:a]adelay={delay_ms}:all=1[{label}]")
            labels.append(f"[{label}]")

        filter_complex = ";".join(filters)
        filter_complex += f";{''.join(labels)}amix=inputs={len(labels)}:duration=longest[aout]"
        args.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                "[aout]",
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(settings.tts_sample_rate),
                "-ac",
                "1",
                str(output_path),
            ]
        )
        self._run_ffmpeg(args, "Could not align TTS audio by timestamp.")

    def _run_ffmpeg(self, args: list[str], user_message: str) -> None:
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
            message = f"{user_message} {detail}" if detail else user_message
            raise ProcessingError("TTS_FAILED", message) from exc

    def _write_silence(self, output_path: Path, duration_seconds: float, sample_rate: int) -> None:
        total_frames = max(int(round(duration_seconds * sample_rate)), 1)
        self._write_pcm(output_path, b"\x00\x00" * total_frames, sample_rate)

    @staticmethod
    def _write_pcm(output_path: Path, pcm: bytes, sample_rate: int) -> None:
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm)
