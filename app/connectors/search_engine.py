from urllib.parse import urlparse

import httpx

from app.connectors.base import RawCandidate, RawContent
from app.models import Platform
from app.services.query_parser import SearchIntent


_PLATFORM_DOMAINS: tuple[tuple[Platform, tuple[str, ...]], ...] = (
    (Platform.tiktok, ("tiktok.com",)),
    (Platform.instagram, ("instagram.com",)),
    (Platform.youtube, ("youtube.com", "youtu.be")),
)


def extract_platform_from_url(url: str) -> Platform:
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
    except ValueError:
        return Platform.web

    if not hostname:
        return Platform.web

    host = hostname.lower().rstrip(".")
    for platform, domains in _PLATFORM_DOMAINS:
        if any(_is_host_or_subdomain(host, domain) for domain in domains):
            return platform
    return Platform.web


def _is_host_or_subdomain(host: str, domain: str) -> bool:
    return host == domain or host.endswith(f".{domain}")


class SearchEngineConnector:
    name = "search_engine"
    search_url = "https://www.googleapis.com/customsearch/v1"

    def __init__(
        self,
        api_key: str,
        search_engine_id: str,
        client: httpx.Client | None = None,
    ):
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.client = client or httpx.Client(timeout=20)

    def build_search_params(self, intent: SearchIntent) -> dict[str, str | int]:
        terms = " ".join(intent.core_terms or intent.expanded_terms or [intent.input_text])
        site_filters = " OR ".join(_site_filter(platform) for platform in intent.platforms)
        query = f"{terms} ({site_filters}) influencer creator contact".strip()
        return {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query,
            "num": 10,
        }

    def search(self, intent: SearchIntent) -> list[RawCandidate]:
        if not self.api_key or not self.search_engine_id:
            return []

        response = self.client.get(self.search_url, params=self.build_search_params(intent))
        response.raise_for_status()
        payload = response.json()

        candidates: list[RawCandidate] = []
        seen_urls: set[str] = set()
        requested_platforms = set(intent.platforms)
        for item in payload.get("items", []):
            if not isinstance(item, dict):
                continue
            link = item.get("link", "")
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            if not isinstance(link, str) or not isinstance(title, str):
                continue
            platform = extract_platform_from_url(link)
            if platform == Platform.web or platform not in requested_platforms or link in seen_urls:
                continue
            seen_urls.add(link)
            display_name = _display_name_from_title(title)
            candidates.append(
                RawCandidate(
                    platform=platform,
                    handle=_handle_from_url(link, platform) or display_name,
                    display_name=display_name,
                    profile_url=link,
                    follower_count=0,
                    bio=snippet if isinstance(snippet, str) else "",
                    contents=[
                        RawContent(
                            content_url=link,
                            title=title,
                            description=snippet if isinstance(snippet, str) else "",
                        )
                    ],
                    contacts=[],
                )
            )
        return candidates


def _site_filter(platform: Platform) -> str:
    if platform == Platform.youtube:
        return "site:youtube.com"
    if platform == Platform.tiktok:
        return "site:tiktok.com"
    if platform == Platform.instagram:
        return "site:instagram.com"
    return "site:example.com"


def _display_name_from_title(title: str) -> str:
    return title.split(" - ", 1)[0].strip() or "Unknown Creator"


def _handle_from_url(url: str, platform: Platform) -> str:
    parsed = urlparse(url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        return ""
    first = path_parts[0]
    if platform in {Platform.youtube, Platform.tiktok}:
        return first if first.startswith("@") else f"@{first}"
    if platform == Platform.instagram:
        return f"@{first.lstrip('@')}"
    return first
