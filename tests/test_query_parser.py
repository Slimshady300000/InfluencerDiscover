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
    assert "skincare" in intent.expanded_terms


def test_parse_seed_url():
    intent = parse_search_input("https://www.youtube.com/@creator_a", [Platform.youtube])
    assert intent.input_type == InputType.seed_url
    assert intent.seed_urls == ["https://www.youtube.com/@creator_a"]
