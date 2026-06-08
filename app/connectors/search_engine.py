from urllib.parse import urlparse

from app.models import Platform


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
