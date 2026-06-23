from app.services.video_resolver_service import VideoResolverService


def test_detect_platform_supports_douyin_hosts() -> None:
    assert VideoResolverService.detect_platform("https://www.douyin.com/video/123") == "douyin"
    assert VideoResolverService.detect_platform("https://v.douyin.com/example") == "douyin"


def test_detect_platform_supports_tiktok_hosts() -> None:
    assert VideoResolverService.detect_platform("https://www.tiktok.com/@demo/video/123") == "tiktok"
    assert VideoResolverService.detect_platform("https://vm.tiktok.com/example") == "tiktok"


def test_detect_platform_rejects_other_hosts() -> None:
    assert VideoResolverService.detect_platform("https://example.com/video/123") is None
