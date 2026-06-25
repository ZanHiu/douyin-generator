import json
import random
import re
from pathlib import Path
from urllib.parse import urlencode, urlparse

import httpx

from app.core.config import settings
from app.services.errors import ProcessingError
from app.services.resolvers.cookie_utils import sanitize_cookies
from app.services.resolvers.ms_token_manager import MsTokenManager
from app.services.storage_service import StorageService
from app.services.resolvers.xbogus import XBogus


class DouyinWebResolver:
    _VIDEO_ID_PATTERNS = (
        re.compile(r"/video/(\d+)"),
        re.compile(r"modal_id=(\d+)"),
    )
    _USER_AGENT_POOL = (
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
        ),
    )
    _DETAIL_AID_CANDIDATES = ("6383", "1128")
    _PLAY_ADDR_KEYS = (
        "play_addr_h264",
        "play_addr_265",
        "play_addr_256",
        "play_addr",
    )
    _QUALITY_TARGET_WIDTH = {
        "1440p": 2560,
        "1080p": 1920,
        "720p": 1280,
        "540p": 960,
        "480p": 854,
        "360p": 640,
    }

    def __init__(self, storage: StorageService | None = None) -> None:
        self.storage = storage or StorageService()
        self.user_agent = random.choice(self._USER_AGENT_POOL)
        self.headers = {
            "User-Agent": self.user_agent,
            "Referer": "https://www.douyin.com/?recommend=1",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        self._signer = XBogus(self.user_agent)
        self._ms_token_manager = MsTokenManager(user_agent=self.user_agent)
        self.cookies = sanitize_cookies(self._load_cookies())
        self.cookies["msToken"] = self._ms_token_manager.ensure_ms_token(self.cookies)

    def fetch(self, job_id: str, source_url: str) -> tuple[str, str]:
        normalized_url = self._normalize_url(source_url)
        aweme_id = self._extract_video_id(normalized_url)
        if not aweme_id:
            raise ProcessingError(
                "VIDEO_FETCH_FAILED",
                "Douyin web resolver could not extract aweme_id from the URL.",
            )

        metadata = self._get_video_detail(aweme_id)
        job_dir = self.storage.job_dir(job_id)
        input_path = job_dir / "input.mp4"

        video_info = self._build_no_watermark_url(metadata)
        if not video_info:
            raise ProcessingError(
                "VIDEO_FETCH_FAILED",
                "Douyin web resolver did not find a playable no-watermark video URL.",
            )

        download_url, download_headers = video_info
        self._download_file(download_url, input_path, headers=download_headers)

        if input_path.stat().st_size <= 0:
            raise ProcessingError("VIDEO_FETCH_FAILED", "Downloaded Douyin video file is empty.")

        probe_metadata = self._probe_video(input_path)
        metadata.update(probe_metadata)
        metadata["source_url"] = source_url
        metadata["normalized_source_url"] = normalized_url
        metadata["platform"] = "douyin"
        metadata["downloaded_path"] = str(input_path)
        metadata["resolver"] = "douyin_web"

        metadata_path = self.storage.write_json(job_id, "metadata.json", metadata)
        return str(input_path), metadata_path

    def _normalize_url(self, source_url: str) -> str:
        parsed = urlparse(source_url)
        hostname = (parsed.hostname or "").lower()
        if hostname in {"v.douyin.com", "v.iesdouyin.com"}:
            try:
                with httpx.Client(
                    timeout=15,
                    follow_redirects=True,
                    headers=self.headers,
                ) as client:
                    response = client.get(source_url)
                    response.raise_for_status()
                    return str(response.url)
            except httpx.HTTPError as exc:
                raise ProcessingError(
                    "VIDEO_FETCH_FAILED",
                    f"Could not resolve Douyin short URL. {exc}",
                ) from exc
        return source_url

    def _extract_video_id(self, source_url: str) -> str | None:
        for pattern in self._VIDEO_ID_PATTERNS:
            match = pattern.search(source_url)
            if match:
                return match.group(1)
        return None

    def _load_cookies(self) -> dict[str, str]:
        cookie_file = (settings.douyin_cookies_file or "").strip()
        if not cookie_file:
            return {}

        path = Path(cookie_file)
        if not path.exists():
            raise ProcessingError(
                "VIDEO_FETCH_FAILED",
                f"Configured DOUYIN_COOKIES_FILE does not exist: {path}",
            )

        raw = path.read_text(encoding="utf-8", errors="replace").strip()
        if not raw:
            return {}

        if raw.startswith("{"):
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                return {}
            return {str(key).strip(): str(value).strip() for key, value in payload.items() if str(key).strip()}

        cookies: dict[str, str] = {}
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split("\t")
            if len(parts) >= 7:
                name = parts[-2].strip()
                value = parts[-1].strip()
                if name:
                    cookies[name] = value
        return cookies

    def _default_query(self) -> dict[str, str]:
        return {
            "device_platform": "webapp",
            "aid": "6383",
            "channel": "channel_pc_web",
            "update_version_code": "170400",
            "pc_client_type": "1",
            "pc_libra_divert": "Windows",
            "version_code": "290100",
            "version_name": "29.1.0",
            "cookie_enabled": "true",
            "screen_width": "1536",
            "screen_height": "864",
            "browser_language": "zh-CN",
            "browser_platform": "Win32",
            "browser_name": "Chrome",
            "browser_version": "139.0.0.0",
            "browser_online": "true",
            "engine_name": "Blink",
            "engine_version": "139.0.0.0",
            "os_name": "Windows",
            "os_version": "10",
            "cpu_core_num": "16",
            "device_memory": "8",
            "platform": "PC",
            "downlink": "10",
            "effective_type": "4g",
            "round_trip_time": "200",
            "support_h265": "1",
            "support_dash": "1",
            "uifid": "",
            "msToken": self.cookies["msToken"],
        }

    def _sign_url(self, url: str) -> tuple[str, str]:
        signed_url, _xbogus, user_agent = self._signer.build(url)
        return signed_url, user_agent

    def _build_signed_url(self, path: str, params: dict[str, str]) -> tuple[str, str]:
        query = urlencode(params)
        base_url = f"https://www.douyin.com{path}"
        return self._sign_url(f"{base_url}?{query}")

    def _get_video_detail(self, aweme_id: str) -> dict:
        filtered_reasons: list[str] = []
        for aid in self._DETAIL_AID_CANDIDATES:
            params = self._default_query()
            params["aweme_id"] = aweme_id
            params["aid"] = aid
            data = self._request_json("/aweme/v1/web/aweme/detail/", params)
            detail = data.get("aweme_detail") if isinstance(data, dict) else None
            if isinstance(detail, dict):
                return detail
            filter_info = data.get("filter_detail") if isinstance(data, dict) else None
            if isinstance(filter_info, dict) and filter_info.get("filter_reason"):
                filtered_reasons.append(str(filter_info["filter_reason"]))
                continue
        raise ProcessingError(
            "VIDEO_FETCH_FAILED",
            "Douyin web resolver could not fetch aweme detail."
            + (f" filter_reason={','.join(filtered_reasons)}" if filtered_reasons else ""),
        )

    def _request_json(self, path: str, params: dict[str, str], max_retries: int = 3) -> dict:
        last_error: Exception | None = None
        last_payload: dict | None = None
        last_body_snippet: str | None = None
        last_content_type: str | None = None
        last_payload_type: str | None = None
        last_content_length: int | None = None
        for _ in range(max_retries):
            signed_url, signed_ua = self._build_signed_url(path, params)
            try:
                with httpx.Client(
                    timeout=30,
                    follow_redirects=True,
                    headers={**self.headers, "User-Agent": signed_ua},
                    cookies=self.cookies,
                ) as client:
                    response = client.get(signed_url)
                    response.raise_for_status()
                    if not response.content:
                        last_error = RuntimeError("Empty 200 response")
                        continue
                    last_content_length = len(response.content)
                    last_content_type = response.headers.get("content-type")
                    raw_body = response.text
                    last_body_snippet = raw_body[:240].replace("\r", " ").replace("\n", " ")
                    try:
                        payload = response.json()
                    except json.JSONDecodeError:
                        payload = json.loads(raw_body)
                    if isinstance(payload, dict):
                        last_payload = payload
                        return payload
                    last_payload_type = type(payload).__name__
                    last_error = RuntimeError(f"Unexpected JSON payload type: {last_payload_type}")
            except (httpx.HTTPError, json.JSONDecodeError) as exc:
                last_error = exc
                continue
        payload_hint = ""
        if last_payload:
            status_code = last_payload.get("status_code")
            payload_hint = f" payload_status={status_code!r} keys={sorted(last_payload.keys())}"
        body_hint = ""
        if last_body_snippet is not None or last_content_length is not None or last_payload_type is not None:
            body_hint = (
                f" content_type={last_content_type!r}"
                f" content_length={last_content_length!r}"
                f" payload_type={last_payload_type!r}"
                f" body_snippet={last_body_snippet!r}"
            )
        raise ProcessingError(
            "VIDEO_FETCH_FAILED",
            (
                f"Douyin web resolver request failed. {last_error}{payload_hint}{body_hint}"
                if last_error
                else f"Douyin web resolver request failed.{payload_hint}{body_hint}"
            ),
        )

    def _download_headers(self, user_agent: str | None = None) -> dict[str, str]:
        return {
            "Referer": "https://www.douyin.com/",
            "Origin": "https://www.douyin.com",
            "Accept": "*/*",
            "User-Agent": user_agent or self.user_agent,
        }

    def _download_file(self, url: str, output_path: Path, headers: dict[str, str]) -> None:
        try:
            with httpx.Client(timeout=60, follow_redirects=True, headers=headers) as client:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    with output_path.open("wb") as handle:
                        for chunk in response.iter_bytes():
                            if chunk:
                                handle.write(chunk)
        except httpx.HTTPError as exc:
            raise ProcessingError(
                "VIDEO_FETCH_FAILED",
                f"Douyin web resolver could not download video stream. {exc}",
            ) from exc

    def _probe_video(self, input_path: Path) -> dict:
        import subprocess

        try:
            result = subprocess.run(
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
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            raise ProcessingError(
                "VIDEO_FETCH_FAILED",
                f"Could not inspect downloaded Douyin video. {detail}",
            ) from exc

        data = json.loads(result.stdout)
        video_stream = next(
            (stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"),
            {},
        )
        duration = data.get("format", {}).get("duration")
        return {
            "duration_seconds": float(duration) if duration else None,
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "has_audio_stream": any(stream.get("codec_type") == "audio" for stream in data.get("streams", [])),
            "file_size_bytes": input_path.stat().st_size,
        }

    def _build_no_watermark_url(self, aweme_data: dict) -> tuple[str, dict[str, str]] | None:
        video = aweme_data.get("video", {})
        quality = "highest"
        play_addr = self._pick_preferred_play_addr(video, quality) or {}
        url_candidates = [candidate for candidate in (play_addr.get("url_list") or []) if candidate]
        url_candidates.sort(key=lambda value: 0 if "watermark=0" in value else 1)

        fallback_candidate: tuple[str, dict[str, str]] | None = None
        watermarked_candidate: tuple[str, dict[str, str]] | None = None

        for candidate in url_candidates:
            parsed = urlparse(candidate)
            headers = self._download_headers()
            is_watermarked = self._is_watermarked_media_url(candidate)

            if parsed.netloc.endswith("douyin.com"):
                if "X-Bogus=" not in candidate:
                    signed_url, ua = self._sign_url(candidate)
                    headers = self._download_headers(user_agent=ua)
                    if is_watermarked:
                        watermarked_candidate = watermarked_candidate or (signed_url, headers)
                        continue
                    return signed_url, headers
                if is_watermarked:
                    watermarked_candidate = watermarked_candidate or (candidate, headers)
                    continue
                return candidate, headers

            if is_watermarked:
                watermarked_candidate = watermarked_candidate or (candidate, headers)
            else:
                fallback_candidate = fallback_candidate or (candidate, headers)

        if fallback_candidate:
            return fallback_candidate

        uri = play_addr.get("uri") or video.get("vid") or video.get("download_addr", {}).get("uri")
        if uri:
            ratio = "1080p"
            params = {
                "video_id": uri,
                "ratio": ratio,
                "line": "0",
                "is_play_url": "1",
                "watermark": "0",
                "source": "PackSourceEnum_PUBLISH",
            }
            signed_url, ua = self._build_signed_url("/aweme/v1/play/", params)
            return signed_url, self._download_headers(user_agent=ua)

        if watermarked_candidate:
            return watermarked_candidate

        return None

    @classmethod
    def _pick_preferred_play_addr(cls, video: dict, quality: str = "highest") -> dict | None:
        preferred = cls._pick_play_addr_by_quality(video, quality)
        if preferred:
            return preferred
        if not isinstance(video, dict):
            return None
        primary = video.get("play_addr")
        if isinstance(primary, dict) and primary.get("uri"):
            return primary
        for key in cls._PLAY_ADDR_KEYS:
            candidate = video.get(key)
            if isinstance(candidate, dict) and (cls._extract_first_url(candidate) or candidate.get("uri")):
                return candidate
        return None

    @classmethod
    def _pick_play_addr_by_quality(cls, video: dict, quality: str = "highest") -> dict | None:
        bit_rates = video.get("bit_rate") if isinstance(video, dict) else None
        if not isinstance(bit_rates, list) or not bit_rates:
            return None

        entries: list[tuple[int, int, dict]] = []
        for entry in bit_rates:
            if not isinstance(entry, dict):
                continue
            play_addr = entry.get("play_addr")
            if not isinstance(play_addr, dict):
                continue
            try:
                bit_rate = int(entry.get("bit_rate") or 0)
            except (TypeError, ValueError):
                bit_rate = 0
            width = int(play_addr.get("width") or entry.get("width") or 0)
            entries.append((bit_rate, width, play_addr))
        if not entries:
            return None

        normalized = (quality or "highest").strip().lower()
        if normalized == "lowest":
            entries.sort(key=lambda item: (item[0], item[1]))
            return entries[0][2]

        target_width = cls._QUALITY_TARGET_WIDTH.get(normalized)
        if target_width is not None:
            entries.sort(key=lambda item: (abs(item[1] - target_width), -item[0]))
            return entries[0][2]

        entries.sort(key=lambda item: (-item[0], -item[1]))
        return entries[0][2]

    @staticmethod
    def _extract_first_url(source: object) -> str | None:
        if isinstance(source, dict):
            url_list = source.get("url_list") or source.get("urlList")
            if isinstance(url_list, list) and url_list:
                first = next((item for item in url_list if isinstance(item, str) and item), None)
                return first
            return None
        if isinstance(source, list) and source:
            return next((item for item in source if isinstance(item, str) and item), None)
        if isinstance(source, str) and source:
            return source
        return None

    @staticmethod
    def _is_watermarked_media_url(url: str) -> bool:
        normalized = url.lower()
        return any(
            hint in normalized
            for hint in (
                "tplv-dy-water",
                "dy-water",
                "owner_watermark",
                "watermark_image",
                "watermark=1",
                "playwm",
            )
        )
