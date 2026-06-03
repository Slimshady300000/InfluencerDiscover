from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse

from app.models import Platform


class InputType(StrEnum):
    keyword = "keyword"
    brief = "brief"
    seed_url = "seed_url"


@dataclass(frozen=True)
class SearchIntent:
    input_text: str
    input_type: InputType
    platforms: list[Platform]
    core_terms: list[str]
    expanded_terms: list[str]
    seed_urls: list[str]


DOMAIN_TERMS = {
    "beauty": ["skincare", "makeup", "cosmetics", "护肤", "美容"],
    "skincare": ["beauty", "serum", "moisturizer", "护肤", "敏感肌"],
    "fitness": ["workout", "gym", "health", "健身"],
}


def parse_search_input(input_text: str, platforms: list[Platform]) -> SearchIntent:
    text = input_text.strip()
    seed_urls = [text] if _is_supported_url(text) else []
    input_type = InputType.seed_url if seed_urls else InputType.brief if len(text.split()) >= 4 else InputType.keyword
    words = [w.strip(" ,.;:，。").lower() for w in text.split() if w.strip(" ,.;:，。")]
    core_terms = [w for w in words if not w.startswith("http")]
    if input_type == InputType.seed_url:
        core_terms = []
    expanded_terms = _expand_terms(core_terms)
    return SearchIntent(
        input_text=text,
        input_type=input_type,
        platforms=platforms,
        core_terms=core_terms,
        expanded_terms=expanded_terms,
        seed_urls=seed_urls,
    )


def _is_supported_url(text: str) -> bool:
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.netloc.lower()
    return any(domain in host for domain in ["youtube.com", "tiktok.com", "instagram.com"])


def _expand_terms(core_terms: list[str]) -> list[str]:
    expanded: list[str] = []
    for term in core_terms:
        expanded.append(term)
        expanded.extend(DOMAIN_TERMS.get(term, []))
    seen: set[str] = set()
    return [term for term in expanded if not (term in seen or seen.add(term))]
