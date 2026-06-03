import pytest

from app.models import Platform
from app.services.query_parser import InputType, parse_search_input


def test_parse_keyword_input():
    intent = parse_search_input("skincare", [Platform.youtube])
    assert intent.input_type == InputType.keyword
    assert intent.core_terms == ["skincare"]
    assert intent.platforms == [Platform.youtube]


def test_parse_brief_input_expands_terms():
    text = "Southeast Asia beauty brief for skincare serum"
    intent = parse_search_input(text, [Platform.tiktok, Platform.instagram])
    assert intent.input_type == InputType.brief
    assert "beauty" in intent.core_terms
    assert "makeup" in intent.expanded_terms
    assert "cosmetics" in intent.expanded_terms
    assert "makeup" not in intent.core_terms
    assert "cosmetics" not in intent.core_terms


def test_parse_seed_url():
    intent = parse_search_input("https://www.youtube.com/@creator_a", [Platform.youtube])
    assert intent.input_type == InputType.seed_url
    assert intent.seed_urls == ["https://www.youtube.com/@creator_a"]


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/@creator_a",
        "https://m.tiktok.com/@creator",
        "https://www.instagram.com/creator/",
        "https://youtu.be/video_id",
    ],
)
def test_parse_seed_url_accepts_supported_hosts(url):
    intent = parse_search_input(url, [Platform.youtube])
    assert intent.input_type == InputType.seed_url
    assert intent.seed_urls == [url]


@pytest.mark.parametrize(
    "url",
    [
        "https://youtube.com.evil.example/@fake",
        "https://notyoutube.com/@fake",
        "https://example.com/@fake",
    ],
)
def test_parse_seed_url_rejects_unsupported_hosts(url):
    intent = parse_search_input(url, [Platform.youtube])
    assert intent.input_type == InputType.keyword
    assert intent.seed_urls == []


def test_parse_chinese_input_expands_to_english_terms():
    intent = parse_search_input("护肤 美容", [Platform.tiktok])
    assert intent.input_type == InputType.keyword
    assert intent.core_terms == ["护肤", "美容"]
    assert "skincare" in intent.expanded_terms
    assert "beauty" in intent.expanded_terms
    assert "cosmetics" in intent.expanded_terms
