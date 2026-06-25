from app.services.errors import ProcessingError
from app.services.video_resolver_service import VideoResolverService


def test_fetch_uses_douyin_web_resolver_for_douyin(monkeypatch) -> None:
    service = VideoResolverService()
    monkeypatch.setattr(service.douyin_web_resolver, "fetch", lambda job_id, source_url: ("input.mp4", "metadata.json"))

    input_path, metadata_path = service.fetch("job-1", "https://www.douyin.com/video/123")

    assert input_path == "input.mp4"
    assert metadata_path == "metadata.json"


def test_fetch_falls_back_to_browser_resolver_for_douyin(monkeypatch) -> None:
    service = VideoResolverService()

    def fail(_job_id, _source_url):
        raise ProcessingError("VIDEO_FETCH_FAILED", "blocked")

    monkeypatch.setattr(service.douyin_web_resolver, "fetch", fail)
    monkeypatch.setattr(
        service.douyin_browser_resolver,
        "fetch",
        lambda job_id, source_url: ("browser-input.mp4", "browser-metadata.json"),
    )

    input_path, metadata_path = service.fetch("job-1", "https://www.douyin.com/video/123")

    assert input_path == "browser-input.mp4"
    assert metadata_path == "browser-metadata.json"


def test_detect_platform_supports_douyin_hosts() -> None:
    assert VideoResolverService.detect_platform("https://www.douyin.com/video/123") == "douyin"
    assert VideoResolverService.detect_platform("https://v.douyin.com/example") == "douyin"


def test_detect_platform_supports_tiktok_hosts() -> None:
    assert VideoResolverService.detect_platform("https://www.tiktok.com/@demo/video/123") == "tiktok"
    assert VideoResolverService.detect_platform("https://vm.tiktok.com/example") == "tiktok"


def test_detect_platform_rejects_other_hosts() -> None:
    assert VideoResolverService.detect_platform("https://example.com/video/123") is None


def test_detect_platform_supports_iesdouyin_hosts() -> None:
    assert VideoResolverService.detect_platform("https://v.iesdouyin.com/example") == "douyin"
