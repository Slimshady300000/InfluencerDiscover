import httpx

from app.connectors.base import RawCandidate, RawContent
from app.models import Platform
from app.services.query_parser import SearchIntent


class YouTubeConnector:
    name = "youtube"
    search_url = "https://www.googleapis.com/youtube/v3/search"

    def __init__(self, api_key: str, client: httpx.Client | None = None):
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=20)

    def build_search_params(self, intent: SearchIntent) -> dict[str, str | int]:
        query = " ".join(intent.core_terms or intent.expanded_terms)
        return {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 25,
            "key": self.api_key,
        }

    def search(self, intent: SearchIntent) -> list[RawCandidate]:
        if not self.api_key:
            return []

        response = self.client.get(self.search_url, params=self.build_search_params(intent))
        response.raise_for_status()
        payload = response.json()

        candidates: list[RawCandidate] = []
        for item in payload.get("items", []):
            snippet = item.get("snippet", {})
            channel_id = snippet.get("channelId", "")
            channel_title = snippet.get("channelTitle", "Unknown YouTube Creator")
            video_id = item.get("id", {}).get("videoId", "")
            description = snippet.get("description", "")
            candidates.append(
                RawCandidate(
                    platform=Platform.youtube,
                    handle=channel_title,
                    display_name=channel_title,
                    profile_url=f"https://www.youtube.com/channel/{channel_id}",
                    follower_count=0,
                    bio=description,
                    contents=[
                        RawContent(
                            content_url=f"https://www.youtube.com/watch?v={video_id}",
                            title=snippet.get("title", ""),
                            description=description,
                        )
                    ],
                    contacts=[],
                )
            )
        return candidates
