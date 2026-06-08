from collections.abc import Callable

import httpx

from app.connectors.base import RawCandidate, RawContent
from app.models import Platform
from app.services.query_parser import SearchIntent


class YouTubeConnector:
    name = "youtube"
    search_url = "https://www.googleapis.com/youtube/v3/search"

    def __init__(
        self,
        api_key: str,
        client: httpx.Client | None = None,
        client_factory: Callable[..., httpx.Client] = httpx.Client,
    ):
        self.api_key = api_key
        self._owns_client = client is None
        self.client = client or client_factory(timeout=20)

    def __enter__(self) -> "YouTubeConnector":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

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
            if not isinstance(item, dict):
                continue
            snippet = item.get("snippet", {})
            item_id = item.get("id", {})
            if not isinstance(snippet, dict) or not isinstance(item_id, dict):
                continue
            channel_id = snippet.get("channelId", "")
            video_id = item_id.get("videoId", "")
            if not channel_id or not video_id:
                continue
            channel_title = snippet.get("channelTitle", "Unknown YouTube Creator")
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
