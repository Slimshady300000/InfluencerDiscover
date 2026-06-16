from app.connectors.web_crawler import (
    WebCrawlerConnector,
    extract_public_profile_metadata,
)
from app.models import Platform
from app.services.query_parser import parse_search_input


class FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class FakeClient:
    def __init__(self, responses: dict[str, str]):
        self.responses = responses
        self.requests: list[tuple[str, dict | None]] = []

    def get(self, url, params=None, headers=None, follow_redirects=None):
        self.requests.append((url, params))
        if params and "q" in params:
            query = str(params["q"])
            if "site:youtube.com" in query:
                return FakeResponse(self.responses["youtube_search"])
            if "site:tiktok.com" in query:
                return FakeResponse(self.responses["tiktok_search"])
            if "site:instagram.com" in query:
                return FakeResponse(self.responses["instagram_search"])
        return FakeResponse(self.responses.get(str(url), ""))


def test_web_crawler_connector_parses_platform_search_results_and_profile_metadata():
    responses = {
        "youtube_search": """
          <html><body>
            <div class="result">
              <a href="/url?q=https%3A%2F%2Fwww.youtube.com%2F%40glowlab&sa=U">
                Glow Lab - YouTube
              </a>
              <p>Skincare creator contact and reviews.</p>
            </div>
          </body></html>
        """,
        "tiktok_search": """
          <html><body>
            <a href="https://www.tiktok.com/@barrierboss">Barrier Boss</a>
            <span>Short-form skincare routines.</span>
          </body></html>
        """,
        "instagram_search": """
          <html><body>
            <a href="https://www.instagram.com/skin.notes/">Skin Notes</a>
            <div>Beauty reels and product tests.</div>
          </body></html>
        """,
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
            <title>Skin Notes • Instagram</title>
            <meta property="og:description" content="Sensitive skin notes and product testing.">
          </head><body>Public profile.</body></html>
        """,
    }
    connector = WebCrawlerConnector(client=FakeClient(responses))
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
    assert candidates[0].contents[0].title == "Glow Lab - YouTube"
    assert candidates[0].data_source == "real_public"
    assert connector.last_status["youtube"]["query"].startswith("site:youtube.com skincare")
    assert connector.last_status["youtube"]["parsed_count"] == 1
    assert connector.last_status["youtube"]["fetched_count"] == 1


def test_web_crawler_connector_filters_non_targets_duplicates_and_bad_urls():
    responses = {
        "youtube_search": "<html><body></body></html>",
        "tiktok_search": """
          <html><body>
            <a href="https://www.tiktok.com/@barrierboss">Barrier Boss</a>
            <a href="https://www.tiktok.com/@barrierboss">Duplicate Boss</a>
            <a href="https://example.com/not-target">Off platform</a>
            <a href="not a url">Bad URL</a>
          </body></html>
        """,
        "https://www.tiktok.com/@barrierboss": """
          <html><head><title>Barrier Boss | TikTok</title></head>
          <body>Public creator profile.</body></html>
        """,
    }
    connector = WebCrawlerConnector(client=FakeClient(responses))
    intent = parse_search_input("skincare", [Platform.tiktok])

    candidates = connector.search(intent)

    assert len(candidates) == 1
    assert candidates[0].profile_url == "https://www.tiktok.com/@barrierboss"
    assert connector.last_status["tiktok"]["skipped_count"] == 2


def test_web_crawler_connector_ignores_navigation_links_in_search_status():
    responses = {
        "youtube_search": """
          <html><body>
            <a href="#">Skip to content</a>
            <a href="javascript:void(0)">Menu</a>
            <a href="/html/">Search home</a>
          </body></html>
        """,
    }
    connector = WebCrawlerConnector(client=FakeClient(responses))
    intent = parse_search_input("skincare", [Platform.youtube])

    candidates = connector.search(intent)

    assert candidates == []
    assert connector.last_status["youtube"]["returned_count"] == 0
    assert connector.last_status["youtube"]["skipped_count"] == 0
    assert connector.last_status["youtube"]["errors"] == ["search source returned no usable links"]


def test_extract_public_profile_metadata_gets_title_description_email_and_text():
    html = """
      <html><head>
        <title>Creator Profile</title>
        <meta name="description" content="Public skincare profile. Email: collab@example.com">
      </head>
      <body><script>ignore()</script><p>Visible public text.</p></body></html>
    """

    metadata = extract_public_profile_metadata(html)

    assert metadata.title == "Creator Profile"
    assert metadata.description == "Public skincare profile. Email: collab@example.com"
    assert metadata.emails == ["collab@example.com"]
    assert "Visible public text." in metadata.text
    assert "ignore()" not in metadata.text
