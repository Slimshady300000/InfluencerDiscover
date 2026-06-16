from dataclasses import dataclass
import re
from urllib.parse import parse_qs, unquote, urlparse, urlunparse

from bs4 import BeautifulSoup
import httpx

from app.connectors.base import RawCandidate, RawContact, RawContent
from app.connectors.search_engine import extract_platform_from_url
from app.models import Platform
from app.services.query_parser import SearchIntent


_EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; InfluencerDiscoveryCrawler/0.1; "
        "+https://example.invalid/public-search)"
    )
}


@dataclass(frozen=True)
class PublicProfileMetadata:
    title: str
    description: str
    emails: list[str]
    text: str


@dataclass(frozen=True)
class SearchResultLink:
    url: str
    title: str
    snippet: str


class WebCrawlerConnector:
    name = "web_crawler"
    search_url = "https://www.bing.com/search"
    max_per_platform = 20

    def __init__(
        self,
        client: httpx.Client | None = None,
        search_url: str | None = None,
        max_per_platform: int | None = None,
    ):
        self.client = client or httpx.Client(timeout=20)
        self.search_url = search_url or self.search_url
        self.max_per_platform = max_per_platform or self.max_per_platform
        self.last_status: dict[str, dict] = {}

    def search(self, intent: SearchIntent) -> list[RawCandidate]:
        candidates: list[RawCandidate] = []
        seen_urls: set[str] = set()
        platforms = intent.platforms or [Platform.youtube]

        for platform in platforms:
            query = _build_public_search_query(intent, platform)
            platform_status = {
                "query": query,
                "returned_count": 0,
                "parsed_count": 0,
                "fetched_count": 0,
                "skipped_count": 0,
                "errors": [],
            }
            self.last_status[platform.value] = platform_status

            try:
                response = self.client.get(
                    self.search_url,
                    params={"q": query, "count": self.max_per_platform},
                    headers=_HEADERS,
                    follow_redirects=True,
                )
                response.raise_for_status()
            except Exception as exc:
                platform_status["errors"].append(f"search request failed: {exc}")
                continue

            result_links = _parse_search_result_links(response.text, platform)
            platform_status["returned_count"] = len(result_links)
            for result in result_links:
                if len([item for item in candidates if item.platform == platform]) >= self.max_per_platform:
                    break

                normalized_url = _normalize_public_url(result.url)
                detected_platform = extract_platform_from_url(normalized_url)
                if (
                    not normalized_url
                    or detected_platform != platform
                    or normalized_url in seen_urls
                ):
                    platform_status["skipped_count"] += 1
                    continue

                seen_urls.add(normalized_url)
                metadata = PublicProfileMetadata(title="", description="", emails=[], text="")
                try:
                    profile_response = self.client.get(
                        normalized_url,
                        headers=_HEADERS,
                        follow_redirects=True,
                    )
                    profile_response.raise_for_status()
                    metadata = extract_public_profile_metadata(profile_response.text)
                    platform_status["fetched_count"] += 1
                except Exception as exc:
                    platform_status["errors"].append(
                        f"profile fetch failed for {normalized_url}: {exc}"
                    )

                display_name = _display_name_from_title(metadata.title or result.title)
                bio = _best_bio(metadata, result.snippet)
                candidates.append(
                    RawCandidate(
                        platform=platform,
                        handle=_handle_from_url(normalized_url, platform) or display_name,
                        display_name=display_name,
                        profile_url=normalized_url,
                        follower_count=0,
                        data_source="real_public",
                        bio=bio,
                        contents=[
                            RawContent(
                                content_url=normalized_url,
                                title=result.title or metadata.title or display_name,
                                description=result.snippet or bio,
                            )
                        ],
                        contacts=[
                            RawContact(
                                contact_type="email",
                                value=email,
                                source_url=normalized_url,
                                is_public=True,
                            )
                            for email in metadata.emails
                        ],
                    )
                )
                platform_status["parsed_count"] += 1

            if platform_status["parsed_count"] == 0 and not platform_status["errors"]:
                platform_status["errors"].append("search source returned no usable links")

        return candidates


def extract_public_profile_metadata(html: str) -> PublicProfileMetadata:
    soup = BeautifulSoup(html, "html.parser")
    for hidden in soup(["script", "style", "noscript"]):
        hidden.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    description = _meta_content(
        soup,
        (
            {"name": "description"},
            {"property": "og:description"},
            {"name": "twitter:description"},
        ),
    )
    text = _collapse_whitespace(soup.get_text(" ", strip=True))
    email_source = " ".join(part for part in [description, text] if part)
    emails = _extract_emails(email_source)
    return PublicProfileMetadata(
        title=_collapse_whitespace(title),
        description=_collapse_whitespace(description),
        emails=emails,
        text=text,
    )


def _build_public_search_query(intent: SearchIntent, platform: Platform) -> str:
    terms = " ".join(intent.core_terms or intent.expanded_terms or [intent.input_text]).strip()
    if not terms:
        terms = intent.input_text
    return f"{_site_filter(platform)} {terms} creator contact".strip()


def _site_filter(platform: Platform) -> str:
    if platform == Platform.youtube:
        return "site:youtube.com"
    if platform == Platform.tiktok:
        return "site:tiktok.com"
    if platform == Platform.instagram:
        return "site:instagram.com"
    return "site:example.com"


def _parse_search_result_links(html: str, platform: Platform) -> list[SearchResultLink]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[SearchResultLink] = []
    for anchor in soup.find_all("a", href=True):
        raw_url = _unwrap_search_url(str(anchor.get("href", "")))
        if not raw_url:
            continue

        title = _collapse_whitespace(anchor.get_text(" ", strip=True))
        snippet = _snippet_from_anchor(anchor, title)
        if extract_platform_from_url(raw_url) != platform:
            results.append(SearchResultLink(url=raw_url, title=title, snippet=snippet))
            continue

        results.append(SearchResultLink(url=raw_url, title=title, snippet=snippet))
    return results


def _unwrap_search_url(href: str) -> str:
    href = href.strip()
    parsed = urlparse(href)
    query_params = parse_qs(parsed.query)
    for key in ("q", "url", "u", "uddg"):
        for value in query_params.get(key, []):
            decoded = unquote(value)
            if _is_http_url(decoded):
                return decoded

    if _is_http_url(href):
        outer_params = parse_qs(urlparse(href).query)
        for key in ("q", "url", "u", "uddg"):
            for value in outer_params.get(key, []):
                decoded = unquote(value)
                if _is_http_url(decoded):
                    return decoded
        return href

    return ""


def _normalize_public_url(url: str) -> str:
    if not _is_http_url(url):
        return ""
    parsed = urlparse(url)
    if not parsed.hostname:
        return ""
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            "",
            parsed.query,
            "",
        )
    )


def _is_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _snippet_from_anchor(anchor, title: str) -> str:
    parent = anchor.find_parent()
    if parent is None:
        return ""
    parent_text = _collapse_whitespace(parent.get_text(" ", strip=True))
    if title and parent_text.startswith(title):
        parent_text = parent_text[len(title) :].strip()
    return parent_text[:500]


def _meta_content(soup: BeautifulSoup, selectors: tuple[dict[str, str], ...]) -> str:
    for selector in selectors:
        tag = soup.find("meta", attrs=selector)
        if tag and tag.get("content"):
            return str(tag["content"])
    return ""


def _best_bio(metadata: PublicProfileMetadata, snippet: str) -> str:
    if metadata.description:
        return metadata.description
    if snippet:
        return snippet
    return metadata.text[:280]


def _extract_emails(text: str) -> list[str]:
    seen: set[str] = set()
    emails: list[str] = []
    for match in _EMAIL_RE.findall(text):
        email = match.strip(".,;:)]}").lower()
        if email not in seen:
            seen.add(email)
            emails.append(email)
    return emails


def _display_name_from_title(title: str) -> str:
    cleaned = _collapse_whitespace(title)
    for separator in (" - ", " | ", "•"):
        if separator in cleaned:
            cleaned = cleaned.split(separator, 1)[0].strip()
    return cleaned or "Unknown Creator"


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


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())
