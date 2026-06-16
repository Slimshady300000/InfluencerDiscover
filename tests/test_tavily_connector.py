from app.connectors.tavily import TavilyConnector
from app.models import Platform
from app.services.query_parser import parse_search_input


class FakeResponse:
    def __init__(self, payload=None, text=""):
        self.payload = payload or {}
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self):
        self.posts = []
        self.gets = []

    def post(self, url, json=None, headers=None):
        self.posts.append((url, json, headers))
        domain = json["include_domains"][0]
        if domain == "youtube.com":
            return FakeResponse(
                {
                    "results": [
                        {
                            "title": "Glow Lab - YouTube",
                            "url": "https://www.youtube.com/@glowlab",
                            "content": "Skincare creator contact and reviews.",
                            "score": 0.91,
                        },
                        {
                            "title": "Watch page should be skipped",
                            "url": "https://www.youtube.com/watch?v=abc",
                            "content": "Not a profile URL.",
                            "score": 0.4,
                        },
                    ]
                }
            )
        if domain == "tiktok.com":
            return FakeResponse(
                {
                    "results": [
                        {
                            "title": "Barrier Boss",
                            "url": "https://www.tiktok.com/@barrierboss/video/123",
                            "content": "Short-form skincare routines.",
                            "score": 0.88,
                        }
                    ]
                }
            )
        return FakeResponse(
            {
                "results": [
                    {
                        "title": "Skin Notes",
                        "url": "https://www.instagram.com/skin.notes/",
                        "content": "Beauty reels and product tests.",
                        "score": 0.86,
                    },
                    {
                        "title": "Duplicate Skin Notes",
                        "url": "https://www.instagram.com/skin.notes/",
                        "content": "Duplicate should be skipped.",
                        "score": 0.72,
                    },
                    {
                        "title": "Off platform",
                        "url": "https://example.com/skin.notes",
                        "content": "Not a target platform.",
                        "score": 0.1,
                    },
                ]
            }
        )

    def get(self, url, headers=None, follow_redirects=None):
        self.gets.append((url, headers, follow_redirects))
        profiles = {
            "https://www.youtube.com/@glowlab": """
              <html><head>
                <title>Glow Lab - YouTube</title>
                <meta name="description" content="Board-certified skincare routines. Business: hello@glowlab.example">
              </head><body>Public creator profile hello@glowlab.example</body></html>
            """,
            "https://www.tiktok.com/@barrierboss": """
              <html><head><title>Barrier Boss | TikTok</title></head>
              <body>Barrier repair demos. collab@barrier.example</body></html>
            """,
            "https://www.instagram.com/skin.notes/": """
              <html><head>
                <title>Skin Notes - Instagram</title>
                <meta property="og:description" content="Sensitive skin notes and product testing.">
              </head><body>Public profile.</body></html>
            """,
        }
        return FakeResponse(text=profiles.get(url, ""))


def test_tavily_connector_posts_authenticated_domain_scoped_searches():
    client = FakeClient()
    connector = TavilyConnector(api_key="tvly-test", client=client, max_per_platform=5)
    intent = parse_search_input("skincare", [Platform.youtube])

    connector.search(intent)

    url, payload, headers = client.posts[0]
    assert url == "https://api.tavily.com/search"
    assert headers["Authorization"] == "Bearer tvly-test"
    assert payload["query"] == "skincare creator contact"
    assert payload["include_domains"] == ["youtube.com"]
    assert payload["max_results"] == 5
    assert payload["include_answer"] is False
    assert payload["include_raw_content"] is False


def test_tavily_connector_parses_results_and_public_profile_metadata():
    client = FakeClient()
    connector = TavilyConnector(api_key="tvly-test", client=client)
    intent = parse_search_input("skincare", [Platform.youtube, Platform.tiktok, Platform.instagram])

    candidates = connector.search(intent)

    assert [candidate.platform for candidate in candidates] == [
        Platform.youtube,
        Platform.tiktok,
        Platform.instagram,
    ]
    assert candidates[0].display_name == "Glow Lab"
    assert candidates[0].handle == "@glowlab"
    assert candidates[0].profile_url == "https://www.youtube.com/@glowlab"
    assert candidates[0].bio == (
        "Board-certified skincare routines. Business: hello@glowlab.example"
    )
    assert candidates[0].contacts[0].value == "hello@glowlab.example"
    assert candidates[0].contents[0].description == "Skincare creator contact and reviews."
    assert candidates[0].data_source == "real_public"
    assert candidates[1].profile_url == "https://www.tiktok.com/@barrierboss"
    assert candidates[2].profile_url == "https://www.instagram.com/skin.notes/"
    assert connector.last_status["youtube"]["returned_count"] == 2
    assert connector.last_status["youtube"]["parsed_count"] == 1
    assert connector.last_status["youtube"]["skipped_count"] == 1
    assert connector.last_status["instagram"]["skipped_count"] == 2


def test_tavily_connector_empty_key_returns_empty_without_calling_client():
    class FailingClient:
        def post(self, *_args, **_kwargs):
            raise AssertionError("client should not be called without credentials")

    connector = TavilyConnector(api_key="", client=FailingClient())
    intent = parse_search_input("skincare", [Platform.youtube])

    assert connector.search(intent) == []


def test_tavily_connector_uses_channel_slug_for_youtube_legacy_urls():
    class LegacyChannelClient:
        def post(self, *_args, **_kwargs):
            return FakeResponse(
                {
                    "results": [
                        {
                            "title": "Emily DiDonato - YouTube",
                            "url": "https://www.youtube.com/c/EmilyDiDonato",
                            "content": "Skincare creator contact.",
                            "score": 0.9,
                        }
                    ]
                }
            )

        def get(self, *_args, **_kwargs):
            return FakeResponse(
                text="""
                  <html><head>
                    <title>Emily DiDonato - YouTube</title>
                  </head><body>Public creator profile.</body></html>
                """
            )

    connector = TavilyConnector(api_key="tvly-test", client=LegacyChannelClient())
    intent = parse_search_input("skincare", [Platform.youtube])

    candidates = connector.search(intent)

    assert candidates[0].handle == "@EmilyDiDonato"
