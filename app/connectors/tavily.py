from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

import httpx

from app.connectors.base import RawCandidate, RawContact, RawContent
from app.connectors.search_engine import extract_platform_from_url
from app.connectors.web_crawler import (
    PublicProfileMetadata,
    extract_public_profile_metadata,
)
from app.models import Platform
from app.services.query_parser import SearchIntent


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; InfluencerDiscoveryCrawler/0.1; "
        "+https://example.invalid/tavily-search)"
    )
}


@dataclass(frozen=True)
class TavilyResult:
    url: str
    title: str
    content: str
    score: float


class TavilyConnector:
    name = "tavily"
    search_url = "https://api.tavily.com/search"
    max_per_platform = 20

    def __init__(
        self,
        api_key: str,
        client: httpx.Client | None = None,
        max_per_platform: int | None = None,
    ):
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=20)
        self.max_per_platform = max_per_platform or self.max_per_platform
        self.last_status: dict[str, dict] = {}

    def build_search_payload(self, intent: SearchIntent, platform: Platform) -> dict:
        terms = " ".join(intent.core_terms or intent.expanded_terms or [intent.input_text]).strip()
        if not terms:
            terms = intent.input_text
        return {
            "query": f"{terms} creator contact".strip(),
            "search_depth": "basic",
            "topic": "general",
            "max_results": self.max_per_platform,
            "include_answer": False,
            "include_raw_content": False,
            "include_domains": [_platform_domain(platform)],
        }

    def search(self, intent: SearchIntent) -> list[RawCandidate]:
        if not self.api_key:
            return []

        candidates: list[RawCandidate] = []
        seen_urls: set[str] = set()
        platforms = intent.platforms or [Platform.youtube]

        for platform in platforms:
            payload = self.build_search_payload(intent, platform)
            platform_status = {
                "source": self.name,
                "query": payload["query"],
                "returned_count": 0,
                "parsed_count": 0,
                "fetched_count": 0,
                "skipped_count": 0,
                "errors": [],
            }
            self.last_status[platform.value] = platform_status

            try:
                response = self.client.post(
                    self.search_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                results = _parse_tavily_results(response.json())
            except Exception as exc:
                platform_status["errors"].append(f"tavily request failed: {exc}")
                continue

            platform_status["returned_count"] = len(results)
            for result in results:
                if len([item for item in candidates if item.platform == platform]) >= self.max_per_platform:
                    break

                profile_url = _canonical_profile_url(result.url, platform)
                if not profile_url or profile_url in seen_urls:
                    platform_status["skipped_count"] += 1
                    continue

                seen_urls.add(profile_url)
                metadata = PublicProfileMetadata(title="", description="", emails=[], text="")
                try:
                    profile_response = self.client.get(
                        profile_url,
                        headers=_HEADERS,
                        follow_redirects=True,
                    )
                    profile_response.raise_for_status()
                    metadata = extract_public_profile_metadata(profile_response.text)
                    platform_status["fetched_count"] += 1
                except Exception as exc:
                    platform_status["errors"].append(
                        f"profile fetch failed for {profile_url}: {exc}"
                    )

                display_name = _display_name_from_title(metadata.title or result.title)
                bio = _best_bio(metadata, result.content)
                candidates.append(
                    RawCandidate(
                        platform=platform,
                        handle=_handle_from_url(profile_url, platform) or display_name,
                        display_name=display_name,
                        profile_url=profile_url,
                        follower_count=0,
                        data_source="real_public",
                        bio=bio,
                        contents=[
                            RawContent(
                                content_url=profile_url,
                                title=result.title or metadata.title or display_name,
                                description=result.content or bio,
                            )
                        ],
                        contacts=[
                            RawContact(
                                contact_type="email",
                                value=email,
                                source_url=profile_url,
                                is_public=True,
                            )
                            for email in metadata.emails
                        ],
                    )
                )
                platform_status["parsed_count"] += 1

            if platform_status["parsed_count"] == 0 and not platform_status["errors"]:
                platform_status["errors"].append("tavily returned no usable profile links")

        return candidates


def _parse_tavily_results(payload: dict) -> list[TavilyResult]:
    results: list[TavilyResult] = []
    for item in payload.get("results", []):
        if not isinstance(item, dict):
            continue
        url = item.get("url", "")
        title = item.get("title", "")
        content = item.get("content", "")
        score = item.get("score", 0.0)
        if not isinstance(url, str) or not isinstance(title, str):
            continue
        results.append(
            TavilyResult(
                url=url,
                title=title,
                content=content if isinstance(content, str) else "",
                score=float(score) if isinstance(score, int | float) else 0.0,
            )
        )
    return results


def _platform_domain(platform: Platform) -> str:
    if platform == Platform.youtube:
        return "youtube.com"
    if platform == Platform.tiktok:
        return "tiktok.com"
    if platform == Platform.instagram:
        return "instagram.com"
    return "example.com"


def _canonical_profile_url(url: str, platform: Platform) -> str:
    if extract_platform_from_url(url) != platform:
        return ""

    try:
        parsed = urlparse(url)
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""

    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        return ""

    path = _profile_path(path_parts, platform)
    if not path:
        return ""

    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def _profile_path(path_parts: list[str], platform: Platform) -> str:
    first = path_parts[0]
    if platform == Platform.youtube:
        if first.startswith("@"):
            return f"/{first}"
        if first in {"channel", "c", "user"} and len(path_parts) >= 2:
            return f"/{first}/{path_parts[1]}"
        return ""

    if platform == Platform.tiktok:
        return f"/{first}" if first.startswith("@") else ""

    if platform == Platform.instagram:
        reserved = {
            "accounts",
            "explore",
            "p",
            "reel",
            "reels",
            "stories",
            "tags",
        }
        if first.lower() in reserved:
            return ""
        return f"/{first}/"

    return ""


def _display_name_from_title(title: str) -> str:
    cleaned = " ".join(title.split())
    for separator in (" - ", " | ", " \u2014 "):
        if separator in cleaned:
            cleaned = cleaned.split(separator, 1)[0].strip()
    return cleaned or "Unknown Creator"


def _handle_from_url(url: str, platform: Platform) -> str:
    parsed = urlparse(url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        return ""

    first = path_parts[0]
    if platform == Platform.youtube and first in {"channel", "c", "user"} and len(path_parts) >= 2:
        return f"@{path_parts[1].lstrip('@')}"
    if platform in {Platform.youtube, Platform.tiktok}:
        return first if first.startswith("@") else f"@{first}"
    if platform == Platform.instagram:
        return f"@{first.lstrip('@')}"
    return first


def _best_bio(metadata: PublicProfileMetadata, snippet: str) -> str:
    if metadata.description:
        return metadata.description
    if snippet:
        return snippet
    return metadata.text[:280]
