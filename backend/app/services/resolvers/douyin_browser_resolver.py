import asyncio
import json
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import settings
from app.services.errors import ProcessingError
from app.services.resolvers.cookie_utils import sanitize_cookies
from app.services.resolvers.douyin_web_resolver import DouyinWebResolver
from app.services.storage_service import StorageService


class DouyinBrowserResolver:
    _DETAIL_ENDPOINT = "/aweme/v1/web/aweme/detail/"

    def __init__(self, storage: StorageService | None = None) -> None:
        self.storage = storage or StorageService()
        self.web_resolver = DouyinWebResolver(self.storage)

    def fetch(self, job_id: str, source_url: str) -> tuple[str, str]:
        try:
            return asyncio.run(self._fetch_async(job_id, source_url))
        except ProcessingError:
            raise
        except RuntimeError as exc:
            if "asyncio.run() cannot be called" in str(exc):
                raise ProcessingError(
                    "VIDEO_FETCH_FAILED",
                    "Douyin browser fallback could not start its event loop.",
                ) from exc
            raise

    async def _fetch_async(self, job_id: str, source_url: str) -> tuple[str, str]:
        try:
            from playwright.async_api import Error as PlaywrightError
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise ProcessingError(
                "MISSING_BINARY",
                "Playwright is not installed. Run `uv sync` and `python -m playwright install chromium`.",
            ) from exc

        timeout_ms = max(settings.douyin_browser_fallback_timeout_seconds, 5) * 1000
        captured_responses = []
        browser = None
        context = None
        page = None

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    headless=settings.douyin_browser_fallback_headless
                )
                context = await browser.new_context(
                    user_agent=self.web_resolver.user_agent,
                    viewport={"width": 1536, "height": 864},
                    java_script_enabled=True,
                )

                browser_cookies = self._load_browser_cookies()
                if browser_cookies:
                    await context.add_cookies(browser_cookies)

                page = await context.new_page()
                page.on("response", lambda response: captured_responses.append(response))

                await page.goto(source_url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except PlaywrightTimeoutError:
                    pass
                await page.wait_for_timeout(1500)

                final_url = page.url
                aweme_id = self.web_resolver._extract_video_id(final_url) or self.web_resolver._extract_video_id(
                    source_url
                )
                if not aweme_id:
                    raise ProcessingError(
                        "VIDEO_FETCH_FAILED",
                        "Douyin browser fallback could not extract aweme_id from the resolved page.",
                    )

                metadata = await self._extract_aweme_detail(captured_responses, aweme_id)
                if metadata is None:
                    raise ProcessingError(
                        "VIDEO_FETCH_FAILED",
                        "Douyin browser fallback could not capture aweme detail in a browser context.",
                    )

                job_dir = self.storage.job_dir(job_id)
                input_path = job_dir / "input.mp4"
                video_info = self.web_resolver._build_no_watermark_url(metadata)
                if not video_info:
                    raise ProcessingError(
                        "VIDEO_FETCH_FAILED",
                        "Douyin browser fallback did not find a playable no-watermark video URL.",
                    )

                download_url, download_headers = video_info
                self.web_resolver._download_file(download_url, input_path, headers=download_headers)

                if input_path.stat().st_size <= 0:
                    raise ProcessingError(
                        "VIDEO_FETCH_FAILED",
                        "Downloaded Douyin video file is empty.",
                    )

                probe_metadata = self._probe_video(input_path)
                metadata.update(probe_metadata)
                metadata["source_url"] = source_url
                metadata["normalized_source_url"] = final_url
                metadata["platform"] = "douyin"
                metadata["downloaded_path"] = str(input_path)
                metadata["resolver"] = "douyin_browser"

                metadata_path = self.storage.write_json(job_id, "metadata.json", metadata)
                return str(input_path), metadata_path
        finally:
            if page is not None:
                try:
                    await page.close()
                except PlaywrightError:
                    pass
            if context is not None:
                try:
                    await context.close()
                except PlaywrightError:
                    pass
            if browser is not None:
                try:
                    await browser.close()
                except PlaywrightError:
                    pass

    async def _extract_aweme_detail(self, responses: list, aweme_id: str) -> dict | None:
        for response in reversed(responses):
            if self._DETAIL_ENDPOINT not in response.url:
                continue
            if response.status != 200:
                continue
            try:
                payload = await response.json()
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            detail = payload.get("aweme_detail")
            if not isinstance(detail, dict):
                continue
            current_aweme_id = str(detail.get("aweme_id") or detail.get("awemeId") or "")
            if current_aweme_id == aweme_id:
                return detail
        return None

    def _load_browser_cookies(self) -> list[dict]:
        cookie_file = (settings.douyin_cookies_file or "").strip()
        if not cookie_file:
            return []

        path = Path(cookie_file)
        if not path.exists():
            raise ProcessingError(
                "VIDEO_FETCH_FAILED",
                f"Configured DOUYIN_COOKIES_FILE does not exist: {path}",
            )

        raw = path.read_text(encoding="utf-8", errors="replace")
        cookies: list[dict] = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split("\t")
            if len(parts) < 7:
                continue
            domain, include_subdomains, path_value, secure, expires, name, value = parts[:7]
            sanitized = sanitize_cookies({name.strip(): value.strip()})
            if not sanitized:
                continue
            cookie = {
                "name": next(iter(sanitized.keys())),
                "value": next(iter(sanitized.values())),
                "domain": domain.strip(),
                "path": path_value.strip() or "/",
                "secure": secure.strip().upper() == "TRUE",
                "httpOnly": False,
            }
            expires_raw = expires.strip()
            if expires_raw.isdigit():
                cookie["expires"] = float(expires_raw)
            if include_subdomains.strip().upper() == "FALSE" and cookie["domain"].startswith("."):
                cookie["domain"] = cookie["domain"][1:]
            cookies.append(cookie)
        return cookies

    def _probe_video(self, input_path: Path) -> dict:
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
