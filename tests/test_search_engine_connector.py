from app.connectors.search_engine import SearchEngineConnector, extract_platform_from_url
from app.models import Platform
from app.services.query_parser import parse_search_input


def test_search_engine_connector_builds_custom_search_params():
    connector = SearchEngineConnector(api_key="key", search_engine_id="cx")
    intent = parse_search_input("skincare serum", [Platform.youtube, Platform.tiktok])

    params = connector.build_search_params(intent)

    assert params["key"] == "key"
    assert params["cx"] == "cx"
    assert "skincare" in params["q"]
    assert "site:youtube.com" in params["q"]
    assert "site:tiktok.com" in params["q"]
    assert params["num"] == 10


def test_search_engine_connector_empty_credentials_return_empty_without_calling_client():
    class FailingClient:
        def get(self, *_args, **_kwargs):
            raise AssertionError("client should not be called without credentials")

    connector = SearchEngineConnector(api_key="", search_engine_id="", client=FailingClient())
    intent = parse_search_input("skincare", [Platform.youtube])

    assert connector.search(intent) == []


def test_search_engine_connector_parses_platform_results():
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "items": [
                    {
                        "title": "Creator Alpha - YouTube",
                        "link": "https://www.youtube.com/@creator_alpha",
                        "snippet": "Skincare reviews and routines.",
                    },
                    {
                        "title": "Creator Beta",
                        "link": "https://www.tiktok.com/@creator_beta",
                        "snippet": "Short-form beauty tips.",
                    },
                    {
                        "title": "Creator Gamma",
                        "link": "https://www.instagram.com/creator_gamma/",
                        "snippet": "Beauty reels and product tests.",
                    },
                    {
                        "title": "Off platform",
                        "link": "https://example.com/creator",
                        "snippet": "Not a target platform.",
                    },
                ]
            }

    class FakeClient:
        def __init__(self):
            self.params = None

        def get(self, _url, params):
            self.params = params
            return FakeResponse()

    client = FakeClient()
    connector = SearchEngineConnector(api_key="key", search_engine_id="cx", client=client)
    intent = parse_search_input("skincare", [Platform.youtube, Platform.tiktok, Platform.instagram])

    candidates = connector.search(intent)

    assert client.params == connector.build_search_params(intent)
    assert [candidate.platform for candidate in candidates] == [
        Platform.youtube,
        Platform.tiktok,
        Platform.instagram,
    ]
    assert candidates[0].display_name == "Creator Alpha"
    assert candidates[0].handle == "@creator_alpha"
    assert candidates[0].profile_url == "https://www.youtube.com/@creator_alpha"
    assert candidates[0].contents[0].title == "Creator Alpha - YouTube"
    assert candidates[0].contents[0].description == "Skincare reviews and routines."


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
    assert extract_platform_from_url("http://[::1") == Platform.web
    assert extract_platform_from_url("") == Platform.web
