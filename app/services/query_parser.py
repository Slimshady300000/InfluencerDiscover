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

SUPPORTED_SEED_DOMAINS = {"youtube.com", "youtu.be", "tiktok.com", "instagram.com"}


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
    host = parsed.hostname
    if host is None:
        return False
    normalized_host = host.lower()
    return any(
        normalized_host == domain or normalized_host.endswith(f".{domain}")
        for domain in SUPPORTED_SEED_DOMAINS
    )


def _expand_terms(core_terms: list[str]) -> list[str]:
    expanded: list[str] = []
    for term in core_terms:
        expanded.append(term)
        expanded.extend(_related_domain_terms(term))
    seen: set[str] = set()
    return [term for term in expanded if not (term in seen or seen.add(term))]


def _related_domain_terms(term: str) -> list[str]:
    if term in DOMAIN_TERMS:
        return DOMAIN_TERMS[term]

    related: list[str] = []
    for domain_term, aliases in DOMAIN_TERMS.items():
        if term in aliases:
            related.append(domain_term)
            related.extend(alias for alias in aliases if alias != term)
    return related
