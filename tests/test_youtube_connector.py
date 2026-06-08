from app.connectors.youtube import YouTubeConnector
from app.models import Platform
from app.services.query_parser import parse_search_input


def test_youtube_connector_builds_search_params():
    connector = YouTubeConnector(api_key="key")
    intent = parse_search_input("skincare", [Platform.youtube])
    params = connector.build_search_params(intent)
    assert params["part"] == "snippet"
    assert params["q"] == "skincare"
    assert params["type"] == "video"
    assert params["key"] == "key"


def test_youtube_connector_empty_api_key_returns_empty_without_calling_client():
    class FailingClient:
        def get(self, *_args, **_kwargs):
            raise AssertionError("client should not be called without an API key")

    connector = YouTubeConnector(api_key="", client=FailingClient())
    intent = parse_search_input("skincare", [Platform.youtube])

    assert connector.search(intent) == []


def test_youtube_connector_parses_search_payload():
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "items": [
                    {
                        "id": {"videoId": "video-1"},
                        "snippet": {
                            "channelId": "channel-1",
                            "channelTitle": "Creator One",
                            "title": "Routine",
                            "description": "Daily skincare routine",
                        },
                    }
                ]
            }

    class FakeClient:
        def __init__(self):
            self.params = None

        def get(self, _url, params):
            self.params = params
            return FakeResponse()

    client = FakeClient()
    connector = YouTubeConnector(api_key="key", client=client)
    intent = parse_search_input("skincare", [Platform.youtube])

    candidates = connector.search(intent)

    assert client.params == connector.build_search_params(intent)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.platform == Platform.youtube
    assert candidate.handle == "Creator One"
    assert candidate.display_name == "Creator One"
    assert candidate.profile_url == "https://www.youtube.com/channel/channel-1"
    assert candidate.bio == "Daily skincare routine"
    assert candidate.contents[0].content_url == "https://www.youtube.com/watch?v=video-1"
    assert candidate.contents[0].title == "Routine"
    assert candidate.contents[0].description == "Daily skincare routine"
    assert candidate.contacts == []
