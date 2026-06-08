from app.connectors.search_engine import extract_platform_from_url
from app.models import Platform


def test_extract_platform_from_url():
    assert extract_platform_from_url("https://www.tiktok.com/@creator") == Platform.tiktok
    assert extract_platform_from_url("https://www.instagram.com/creator/") == Platform.instagram
    assert extract_platform_from_url("https://www.youtube.com/@creator") == Platform.youtube


def test_extract_platform_from_url_accepts_known_subdomains_and_youtu_be():
    assert extract_platform_from_url("https://m.tiktok.com/@creator") == Platform.tiktok
    assert extract_platform_from_url("https://help.instagram.com/creator") == Platform.instagram
    assert extract_platform_from_url("https://youtu.be/video-id") == Platform.youtube


def test_extract_platform_from_url_rejects_lookalike_hosts():
    assert extract_platform_from_url("https://notiktok.com/@creator") == Platform.web
    assert extract_platform_from_url("https://evil-tiktok.com/@creator") == Platform.web
    assert extract_platform_from_url("https://tiktok.com.evil.test/@creator") == Platform.web
    assert extract_platform_from_url("https://youtube.com.evil.test/@creator") == Platform.web


def test_extract_platform_from_url_returns_web_for_unknown_or_malformed_urls():
    assert extract_platform_from_url("https://example.com/creator") == Platform.web
    assert extract_platform_from_url("not a url") == Platform.web
    assert extract_platform_from_url("") == Platform.web
