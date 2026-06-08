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
        closed = False

        def get(self, *_args, **_kwargs):
            raise AssertionError("client should not be called without an API key")

    client = FailingClient()
    connector = YouTubeConnector(api_key="", client=client)
    intent = parse_search_input("skincare", [Platform.youtube])

    assert connector.search(intent) == []
    connector.close()
    assert client.closed is False


def test_youtube_connector_closes_owned_client():
    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout
            self.closed = False

        def close(self):
            self.closed = True

    connector = YouTubeConnector(api_key="key", client_factory=FakeClient)

    connector.close()

    assert connector.client.closed is True
    assert connector.client.timeout == 20


def test_youtube_connector_context_manager_closes_owned_client():
    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout
            self.closed = False

        def close(self):
            self.closed = True

    with YouTubeConnector(api_key="key", client_factory=FakeClient) as connector:
        client = connector.client

    assert client.closed is True


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


def test_youtube_connector_skips_malformed_search_items():
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "items": [
                    {"id": {"videoId": "missing-channel"}, "snippet": {"channelTitle": "No Channel"}},
                    {
                        "id": {},
                        "snippet": {"channelId": "channel-2", "channelTitle": "No Video"},
                    },
                    {"id": "not-a-dict", "snippet": {"channelId": "channel-3"}},
                    {"id": {"videoId": "video-4"}, "snippet": "not-a-dict"},
                    {
                        "id": {"videoId": "video-5"},
                        "snippet": {"channelId": ["not", "a", "string"]},
                    },
                    {
                        "id": {"videoId": {"not": "a string"}},
                        "snippet": {"channelId": "channel-6"},
                    },
                    {
                        "id": {"videoId": "video-7"},
                        "snippet": {"channelId": "bad/channel"},
                    },
                    {
                        "id": {"videoId": "abc&list=x"},
                        "snippet": {"channelId": "channel-8"},
                    },
                    {
                        "id": {"videoId": "abc?list=x"},
                        "snippet": {"channelId": "channel-9"},
                    },
                    {
                        "id": {"videoId": " video_10-ok "},
                        "snippet": {
                            "channelId": " channel_10-ok ",
                            "channelTitle": "Creator Ten",
                            "title": "Valid",
                        },
                    },
                ]
            }

    class FakeClient:
        def get(self, _url, params):
            return FakeResponse()

    connector = YouTubeConnector(api_key="key", client=FakeClient())
    intent = parse_search_input("skincare", [Platform.youtube])

    candidates = connector.search(intent)

    assert len(candidates) == 1
    assert candidates[0].profile_url == "https://www.youtube.com/channel/channel_10-ok"
    assert candidates[0].contents[0].content_url == "https://www.youtube.com/watch?v=video_10-ok"
