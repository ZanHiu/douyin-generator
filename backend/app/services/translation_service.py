import json
import re
import time
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.errors import ProcessingError
from app.services.storage_service import StorageService


class TranslationService:
    def __init__(self, storage: StorageService | None = None) -> None:
        self.storage = storage or StorageService()

    def translate(self, job_id: str, transcript_zh_path: str) -> str:
        provider = settings.translation_provider.lower()
        segments = self._load_segments(transcript_zh_path)
        if provider == "mock":
            return self._mock_translate(job_id, segments)
        if provider == "openai":
            return self._openai_translate(job_id, segments)
        if provider == "openrouter":
            return self._openrouter_translate(job_id, segments)
        if provider in {"nine_router", "9router"}:
            return self._nine_router_translate(job_id, segments)
        if provider == "groq":
            return self._groq_translate(job_id, segments)
        if provider == "ollama":
            return self._ollama_translate(job_id, segments)
        raise ProcessingError("TRANSLATION_FAILED", f"Unsupported translation provider: {provider}")

    def _load_segments(self, transcript_zh_path: str) -> list[dict[str, Any]]:
        path = self.storage.resolve_path(transcript_zh_path)
        if not path.exists():
            raise ProcessingError("TRANSLATION_FAILED", "Missing Chinese transcript.")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProcessingError("TRANSLATION_FAILED", "Chinese transcript is not valid JSON.") from exc

        segments = data.get("segments") if isinstance(data, dict) else None
        if not isinstance(segments, list):
            raise ProcessingError("TRANSLATION_FAILED", "Chinese transcript has no valid segments.")
        return segments

    def _mock_translate(self, job_id: str, segments: list[dict[str, Any]]) -> str:
        fallback_texts = [
            "Xin chao moi nguoi, hom nay minh se lam mot mon an.",
            "Cach lam nay rat don gian.",
        ]
        translated = []
        for index, segment in enumerate(segments):
            translated.append(
                {
                    "id": int(segment.get("id", index)),
                    "start": float(segment.get("start", 0.0)),
                    "end": float(segment.get("end", segment.get("start", 0.0))),
                    "text_zh": str(segment.get("text", "")),
                    "text_vi": fallback_texts[index]
                    if index < len(fallback_texts)
                    else f"Mock Vietnamese translation for segment {index + 1}.",
                }
            )
        return self.storage.write_json(job_id, "transcript_vi.json", translated)

    def _openai_translate(self, job_id: str, segments: list[dict[str, Any]]) -> str:
        if not settings.openai_api_key:
            raise ProcessingError("TRANSLATION_FAILED", "OPENAI_API_KEY is not configured.")

        payload = self._build_translation_payload(segments)
        translated_segments, raw_responses = self._translate_with_openai_compatible_provider(
            payload=payload,
            model=settings.translation_model,
            api_key=settings.openai_api_key,
            base_url=None,
            timeout_seconds=settings.openai_request_timeout_seconds,
            batch_size=settings.openai_translation_batch_size,
            provider_name="openai",
        )
        self.storage.write_json(
            job_id,
            "transcript_vi_raw.json",
            {
                "provider": "openai",
                "model": settings.translation_model,
                "responses": raw_responses,
            },
        )
        return self.storage.write_json(job_id, "transcript_vi.json", translated_segments)

    def _nine_router_translate(self, job_id: str, segments: list[dict[str, Any]]) -> str:
        payload = self._build_translation_payload(segments)
        try:
            translated_segments, raw_responses = self._translate_with_openai_compatible_provider(
                payload=payload,
                model=settings.nine_router_model,
                api_key=settings.nine_router_api_key or "local-9router",
                base_url=settings.nine_router_base_url,
                timeout_seconds=settings.nine_router_request_timeout_seconds,
                batch_size=settings.nine_router_translation_batch_size,
                provider_name="nine_router",
            )
        except ProcessingError as exc:
            self._write_translation_raw(
                job_id,
                provider="nine_router",
                model=settings.nine_router_model,
                responses=[],
                error=str(exc),
            )
            raise

        self.storage.write_json(
            job_id,
            "transcript_vi_raw.json",
            {
                "provider": "nine_router",
                "model": settings.nine_router_model,
                "responses": raw_responses,
            },
        )
        return self.storage.write_json(job_id, "transcript_vi.json", translated_segments)

    def _groq_translate(self, job_id: str, segments: list[dict[str, Any]]) -> str:
        if not settings.groq_api_key:
            raise ProcessingError("TRANSLATION_FAILED", "GROQ_API_KEY is not configured.")

        payload = self._build_translation_payload(segments)
        try:
            translated_segments, raw_responses = self._translate_with_openai_compatible_provider(
                payload=payload,
                model=settings.groq_model,
                api_key=settings.groq_api_key,
                base_url=settings.groq_base_url,
                timeout_seconds=settings.groq_request_timeout_seconds,
                batch_size=settings.groq_translation_batch_size,
                provider_name="groq",
            )
        except ProcessingError as exc:
            self._write_translation_raw(
                job_id,
                provider="groq",
                model=settings.groq_model,
                responses=[],
                error=str(exc),
            )
            raise

        self.storage.write_json(
            job_id,
            "transcript_vi_raw.json",
            {
                "provider": "groq",
                "model": settings.groq_model,
                "responses": raw_responses,
            },
        )
        return self.storage.write_json(job_id, "transcript_vi.json", translated_segments)

    def _openrouter_translate(self, job_id: str, segments: list[dict[str, Any]]) -> str:
        if not settings.openrouter_api_key:
            raise ProcessingError("TRANSLATION_FAILED", "OPENROUTER_API_KEY is not configured.")

        payload = self._build_translation_payload(segments)
        try:
            translated_segments, raw_responses = self._translate_with_openai_compatible_provider(
                payload=payload,
                model=settings.openrouter_model,
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
                timeout_seconds=settings.openrouter_request_timeout_seconds,
                batch_size=settings.openrouter_translation_batch_size,
                provider_name="openrouter",
            )
        except ProcessingError as exc:
            self._write_translation_raw(
                job_id,
                provider="openrouter",
                model=settings.openrouter_model,
                responses=[],
                error=str(exc),
            )
            raise

        self.storage.write_json(
            job_id,
            "transcript_vi_raw.json",
            {
                "provider": "openrouter",
                "model": settings.openrouter_model,
                "responses": raw_responses,
            },
        )
        return self.storage.write_json(job_id, "transcript_vi.json", translated_segments)

    @staticmethod
    def _is_rate_limit_error(exc: ProcessingError) -> bool:
        message = str(exc).lower()
        return "429" in message or "rate limit" in message or "too many requests" in message

    @staticmethod
    def _rate_limit_retry_delay_seconds(exc: ProcessingError, provider_name: str) -> float:
        message = str(exc)
        match = re.search(r"retry_after_seconds(?:_raw)?['\"]?:\s*([0-9]+(?:\.[0-9]+)?)", message)
        if match:
            return max(float(match.group(1)) + 1.0, 1.0)
        retry_after = re.search(r"retry-after['\"]?:\s*['\"]?([0-9]+(?:\.[0-9]+)?)", message, re.IGNORECASE)
        if retry_after:
            return max(float(retry_after.group(1)) + 1.0, 1.0)
        reset_tokens = re.search(
            r"x-ratelimit-reset-tokens['\"]?:\s*['\"]?([0-9]+(?:\.[0-9]+)?)([a-z]*)",
            message,
            re.IGNORECASE,
        )
        if reset_tokens:
            return max(TranslationService._duration_to_seconds(reset_tokens.group(1), reset_tokens.group(2)) + 1.0, 1.0)
        if provider_name == "groq":
            return settings.groq_rate_limit_sleep_seconds
        return settings.openrouter_rate_limit_sleep_seconds

    @staticmethod
    def _duration_to_seconds(value: str, unit: str) -> float:
        seconds = float(value)
        normalized_unit = unit.lower()
        if normalized_unit.startswith("ms"):
            return seconds / 1000
        if normalized_unit.startswith("m") and not normalized_unit.startswith("ms"):
            return seconds * 60
        if normalized_unit.startswith("h"):
            return seconds * 3600
        return seconds

    def _translate_with_openai_compatible_provider(
        self,
        payload: list[dict[str, Any]],
        model: str,
        api_key: str,
        base_url: str | None,
        timeout_seconds: float,
        batch_size: int,
        provider_name: str,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        translated_segments: list[dict[str, Any]] = []
        raw_responses = []
        last_error: Exception | None = None
        for _attempt in range(2):
            try:
                translated_segments = []
                raw_responses = []
                for batch_index, batch in enumerate(self._chunk_payload(payload, batch_size)):
                    if batch_index > 0 and provider_name == "groq" and settings.groq_batch_sleep_seconds > 0:
                        time.sleep(settings.groq_batch_sleep_seconds)
                    translated_batch, raw_content = self._request_openai_compatible_translation_with_retry(
                        payload=batch,
                        model=model,
                        api_key=api_key,
                        base_url=base_url,
                        timeout_seconds=timeout_seconds,
                        provider_name=provider_name,
                    )
                    translated_segments.extend(translated_batch)
                    raw_responses.append(raw_content)
                break
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                last_error = exc
        else:
            raise ProcessingError("TRANSLATION_FAILED", f"{provider_name} translation JSON is invalid: {last_error}")
        return translated_segments, raw_responses

    def _request_openai_compatible_translation_with_retry(
        self,
        payload: list[dict[str, Any]],
        model: str,
        api_key: str,
        base_url: str | None,
        timeout_seconds: float,
        provider_name: str,
    ) -> tuple[list[dict[str, Any]], str]:
        attempts_by_provider = {
            "openrouter": settings.openrouter_rate_limit_retry_attempts,
            "groq": settings.groq_rate_limit_retry_attempts,
        }
        attempts = attempts_by_provider.get(provider_name, 1)
        last_error: ProcessingError | None = None
        for attempt in range(max(attempts, 1)):
            try:
                return self._request_openai_compatible_translation(
                    payload=payload,
                    model=model,
                    api_key=api_key,
                    base_url=base_url,
                    timeout_seconds=timeout_seconds,
                    provider_name=provider_name,
                )
            except ProcessingError as exc:
                last_error = exc
                if provider_name not in attempts_by_provider or not self._is_rate_limit_error(exc):
                    raise
                if attempt >= attempts - 1:
                    break
                time.sleep(self._rate_limit_retry_delay_seconds(exc, provider_name))

        raise last_error or ProcessingError("TRANSLATION_FAILED", f"{provider_name} translation failed.")

    def _ollama_translate(self, job_id: str, segments: list[dict[str, Any]]) -> str:
        payload = self._build_translation_payload(segments)
        translated_segments: list[dict[str, Any]] = []
        raw_responses = []
        last_error: Exception | None = None
        for _attempt in range(2):
            raw_responses = []
            try:
                translated_segments = []
                for batch in self._chunk_payload(payload, settings.ollama_translation_batch_size):
                    raw_content = self._request_ollama_translation_content(batch)
                    raw_responses.append(raw_content)
                    translated_segments.extend(self._parse_ollama_batch_with_repair(batch, raw_content, raw_responses))
                break
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                last_error = exc
                self._write_translation_raw(
                    job_id,
                    provider="ollama",
                    model=settings.ollama_model,
                    responses=raw_responses,
                    error=str(exc),
                )
        else:
            raise ProcessingError("TRANSLATION_FAILED", f"Ollama translation JSON is invalid: {last_error}")

        self._write_translation_raw(
            job_id,
            provider="ollama",
            model=settings.ollama_model,
            responses=raw_responses,
        )
        return self.storage.write_json(job_id, "transcript_vi.json", translated_segments)

    def _parse_ollama_batch_with_repair(
        self,
        batch: list[dict[str, Any]],
        raw_content: str,
        raw_responses: list[Any],
    ) -> list[dict[str, Any]]:
        try:
            return self._parse_ollama_translation_content(raw_content, batch)
        except ValueError as exc:
            if "missing translated segment id" not in str(exc) or len(batch) == 1:
                raise

        repaired_segments = []
        for source in batch:
            try:
                single_raw_content = self._request_ollama_translation_content([source])
                raw_responses.append(single_raw_content)
                repaired_segments.extend(self._parse_ollama_translation_content(single_raw_content, [source]))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError, ProcessingError) as exc:
                fallback_segment = self._fallback_translation_segment(source)
                raw_responses.append(
                    {
                        "fallback": True,
                        "id": fallback_segment["id"],
                        "error": str(exc),
                    }
                )
                repaired_segments.append(fallback_segment)
        return repaired_segments

    @staticmethod
    def _fallback_translation_segment(source: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(source.get("id", 0)),
            "start": float(source.get("start", 0.0)),
            "end": float(source.get("end", source.get("start", 0.0))),
            "text_zh": str(source.get("text_zh", "")),
            "text_vi": "Could not translate this segment.",
        }

    def _write_translation_raw(
        self,
        job_id: str,
        provider: str,
        model: str,
        responses: list[Any],
        error: str | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "provider": provider,
            "model": model,
            "responses": responses,
        }
        if error:
            payload["error"] = error
        return self.storage.write_json(job_id, "transcript_vi_raw.json", payload)

    @staticmethod
    def _build_translation_payload(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        payload = [
            {
                "id": int(segment.get("id", index)),
                "start": float(segment.get("start", 0.0)),
                "end": float(segment.get("end", segment.get("start", 0.0))),
                "text_zh": str(segment.get("text", "")),
            }
            for index, segment in enumerate(segments)
            if str(segment.get("text", "")).strip()
        ]
        if not payload:
            raise ProcessingError("TRANSLATION_FAILED", "No Chinese segments available for translation.")
        return payload

    def _request_openai_translation(self, payload: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
        return self._request_openai_compatible_translation(
            payload=payload,
            model=settings.translation_model,
            api_key=settings.openai_api_key or "",
            base_url=None,
            timeout_seconds=settings.openai_request_timeout_seconds,
            provider_name="openai",
        )

    def _request_openai_compatible_translation(
        self,
        payload: list[dict[str, Any]],
        model: str,
        api_key: str,
        base_url: str | None,
        timeout_seconds: float,
        provider_name: str,
    ) -> tuple[list[dict[str, Any]], str]:
        try:
            from openai import OpenAI

            client_kwargs: dict[str, Any] = {
                "api_key": api_key,
                "timeout": timeout_seconds,
            }
            if provider_name in {"openrouter", "groq"}:
                client_kwargs["max_retries"] = 0
            if base_url:
                client_kwargs["base_url"] = base_url

            default_headers = self._openrouter_headers() if provider_name == "openrouter" else None
            if default_headers:
                client_kwargs["default_headers"] = default_headers

            client = OpenAI(**client_kwargs)
            response = client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Translate Douyin/TikTok Chinese transcript segments into natural Vietnamese. "
                            "Keep it concise, conversational, and suitable for subtitles. "
                            "Prefer short Vietnamese lines that can be spoken naturally by TTS. "
                            "Return JSON only with key segments. Each segment must include "
                            "id and text_vi. Do not change ids."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps({"segments": payload}, ensure_ascii=False),
                    },
                ],
            )
        except Exception as exc:
            details = self._openai_compatible_error_details(exc)
            raise ProcessingError("TRANSLATION_FAILED", f"{provider_name} translation failed: {details}") from exc

        content = response.choices[0].message.content or ""
        return self._parse_openai_compatible_translation_content(content, payload), content

    @staticmethod
    def _openrouter_headers() -> dict[str, str]:
        headers = {"X-OpenRouter-Title": settings.openrouter_app_title}
        if settings.openrouter_http_referer:
            headers["HTTP-Referer"] = settings.openrouter_http_referer
        return headers

    @staticmethod
    def _openai_compatible_error_details(exc: Exception) -> str:
        message = TranslationService._summarize_provider_error_message(str(exc))
        parts = [message]
        status_code = getattr(exc, "status_code", None)
        if status_code is not None and str(status_code) not in parts[0]:
            parts.append(f"status_code={status_code}")

        headers = getattr(exc, "headers", None)
        response = getattr(exc, "response", None)
        if headers is None and response is not None:
            headers = getattr(response, "headers", None)
        if headers:
            rate_limit_headers = {}
            for key in (
                "retry-after",
                "x-ratelimit-limit-requests",
                "x-ratelimit-limit-tokens",
                "x-ratelimit-remaining-requests",
                "x-ratelimit-remaining-tokens",
                "x-ratelimit-reset-requests",
                "x-ratelimit-reset-tokens",
            ):
                value = headers.get(key)
                if value is not None:
                    rate_limit_headers[key] = value
            if rate_limit_headers:
                parts.append(f"headers={rate_limit_headers}")
        return " ".join(parts)

    @staticmethod
    def _summarize_provider_error_message(message: str) -> str:
        if "<html" not in message.lower():
            return message

        title_match = re.search(r"<title>\s*(.*?)\s*</title>", message, re.IGNORECASE | re.DOTALL)
        title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else "HTML error response"
        status_match = re.search(r"status_code=([0-9]+)", message)
        domain_match = re.search(r"\|\s*([^|<>\s]+)\s*\|\s*Cloudflare", title)
        domain = domain_match.group(1) if domain_match else None

        if "origin dns error" in title.lower():
            details = "Cloudflare Origin DNS error from translation provider"
            if domain:
                details += f" ({domain})"
            if status_match:
                details += f" status_code={status_match.group(1)}"
            details += ". Check NINE_ROUTER_BASE_URL or restart the Cloudflare tunnel."
            return details

        details = f"Translation provider returned HTML instead of JSON: {title}"
        if status_match:
            details += f" status_code={status_match.group(1)}"
        return details

    def _request_ollama_translation(self, payload: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
        content = self._request_ollama_translation_content(payload)
        return self._parse_ollama_translation_content(content, payload), content

    def _request_ollama_translation_content(self, payload: list[dict[str, Any]]) -> str:
        endpoint = settings.ollama_base_url.rstrip("/") + "/api/chat"
        request_body = {
            "model": settings.ollama_model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You translate Chinese Douyin/TikTok transcript segments into natural Vietnamese. "
                        "Keep Vietnamese concise, conversational, and suitable for subtitles and TTS. "
                        "Return JSON only with key segments. Each segment must include id and text_vi. "
                        "Do not change ids."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({"segments": payload}, ensure_ascii=False),
                },
            ],
        }
        try:
            import httpx

            response = httpx.post(
                endpoint,
                json=request_body,
                timeout=settings.ollama_request_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.ConnectError as exc:
            raise ProcessingError(
                "TRANSLATION_FAILED",
                "Could not connect to Ollama. Start Ollama and pull the model first.",
            ) from exc
        except httpx.HTTPError as exc:
            raise ProcessingError("TRANSLATION_FAILED", f"Ollama request failed: {exc}") from exc

        content = str((data.get("message") or {}).get("content") or "")
        if not content:
            raise ProcessingError("TRANSLATION_FAILED", "Ollama response has no message.content.")
        return content

    @staticmethod
    def _parse_openai_compatible_translation_content(
        content: str,
        source_payload: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        data = json.loads(content)
        segments = data.get("segments") if isinstance(data, dict) else None
        if not isinstance(segments, list):
            raise ValueError("segments must be a list")
        if any(not isinstance(segment, dict) for segment in segments):
            raise ValueError("segments must contain objects")
        return TranslationService._normalize_translation_segments(segments, source_payload)

    @staticmethod
    def _parse_ollama_translation_content(content: str, source_payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
        data = TranslationService._load_translation_json(content)
        segments = data.get("segments") if isinstance(data, dict) else data
        if isinstance(data, dict) and not isinstance(segments, list):
            segments = (
                TranslationService._segments_from_id_map(data)
                or TranslationService._segments_from_single_translation(data)
            )
        if not isinstance(segments, list):
            raise ValueError("segments must be a list")

        return TranslationService._normalize_translation_segments(segments, source_payload)

    @staticmethod
    def _normalize_translation_segments(
        segments: list[Any],
        source_payload: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        translated_by_id = {}
        for index, segment in enumerate(segments):
            if isinstance(segment, str):
                if index >= len(source_payload):
                    continue
                segment_id = int(source_payload[index].get("id", index))
                text_vi = segment.strip()
                if not text_vi:
                    raise ValueError(f"text_vi is empty for segment {segment_id}")
                translated_by_id[segment_id] = text_vi
                continue

            segment_id = int(segment["id"])
            text_vi = str(segment.get("text_vi", "")).strip()
            if not text_vi:
                raise ValueError(f"text_vi is empty for segment {segment_id}")
            translated_by_id[segment_id] = text_vi

        normalized = []
        for index, source in enumerate(source_payload):
            segment_id = int(source.get("id", index))
            if segment_id not in translated_by_id:
                raise ValueError(f"missing translated segment id {segment_id}")
            normalized.append(
                {
                    "id": segment_id,
                    "start": float(source.get("start", 0.0)),
                    "end": float(source.get("end", source.get("start", 0.0))),
                    "text_zh": str(source.get("text_zh", "")),
                    "text_vi": translated_by_id[segment_id],
                }
            )
        return normalized

    @staticmethod
    def _segments_from_id_map(data: dict[str, Any]) -> list[dict[str, Any]] | None:
        mapped_segments = []
        for key, value in data.items():
            segment_id = TranslationService._parse_segment_id_key(str(key))
            if segment_id is None or not isinstance(value, str):
                continue
            mapped_segments.append({"id": segment_id, "text_vi": value})
        if not mapped_segments:
            return None
        return sorted(mapped_segments, key=lambda segment: int(segment["id"]))

    @staticmethod
    def _parse_segment_id_key(key: str) -> int | None:
        if key.isdigit():
            return int(key)
        if key.startswith("id_") and key[3:].isdigit():
            return int(key[3:])
        return None

    @staticmethod
    def _segments_from_single_translation(data: dict[str, Any]) -> list[dict[str, Any]] | None:
        if "id" not in data:
            return None
        text_vi = data.get("text_vi") or data.get("translation") or data.get("text") or data.get("vi")
        if not isinstance(text_vi, str) or not text_vi.strip():
            return None
        return [{"id": int(data["id"]), "text_vi": text_vi.strip()}]

    @staticmethod
    def _load_translation_json(content: str) -> Any:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = json.loads(TranslationService._extract_json_object(content))

        if isinstance(data, dict) and isinstance(data.get("message"), dict):
            nested_content = data["message"].get("content")
            if isinstance(nested_content, str) and nested_content.strip():
                return TranslationService._load_translation_json(nested_content)

        if isinstance(data, dict) and isinstance(data.get("response"), str):
            return TranslationService._load_translation_json(data["response"])

        if isinstance(data, dict) and "segments" not in data:
            translations = data.get("translations") or data.get("translation")
            if isinstance(translations, list):
                return {"segments": translations}
            if isinstance(translations, dict):
                mapped = TranslationService._segments_from_id_map(translations)
                if mapped:
                    return {"segments": mapped}

            for value in data.values():
                if isinstance(value, list):
                    return {"segments": value}
                if isinstance(value, dict):
                    mapped = TranslationService._segments_from_id_map(value)
                    if mapped:
                        return {"segments": mapped}
                if isinstance(value, dict) and "segments" in value:
                    return value
        return data

    @staticmethod
    def _extract_json_object(content: str) -> str:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise json.JSONDecodeError("No JSON object found", content, 0)
        return content[start : end + 1]

    @staticmethod
    def _chunk_payload(payload: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
        safe_batch_size = max(batch_size, 1)
        return [payload[index : index + safe_batch_size] for index in range(0, len(payload), safe_batch_size)]
