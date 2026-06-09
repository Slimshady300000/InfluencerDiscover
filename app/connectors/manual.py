from app.connectors.base import RawCandidate, RawContact, RawContent
from app.models import Platform
from app.services.query_parser import SearchIntent


class ManualConnector:
    name = "manual"
    candidates_per_platform = 8

    def search(self, intent: SearchIntent) -> list[RawCandidate]:
        platforms = intent.platforms or [Platform.youtube]
        return [
            _build_candidate(platform, index)
            for platform in platforms
            for index in range(self.candidates_per_platform)
        ]


_PLATFORM_FIXTURES = {
    Platform.youtube: {
        "handle": "@creator_a",
        "display_name": "Creator A",
        "profile_url": "https://www.youtube.com/@creator_a",
        "follower_count": 310000,
        "bio": "Skincare reviews and beauty routines.",
        "content_url": "https://www.youtube.com/watch?v=creator-a-1",
        "title": "Hydrating serum review",
        "description": "Skincare serum test for sensitive skin.",
        "views": 96000,
        "likes": 6100,
        "comments": 320,
        "contact_type": "email",
        "contact": "business@example.com",
    },
    Platform.tiktok: {
        "handle": "@creator_b",
        "display_name": "Creator B",
        "profile_url": "https://www.tiktok.com/@creator_b",
        "follower_count": 420000,
        "bio": "Short-form skincare demos and viral beauty routines.",
        "content_url": "https://www.tiktok.com/@creator_b/video/1001",
        "title": "Barrier repair routine",
        "description": "Fast skincare routine for dry and sensitive skin.",
        "views": 185000,
        "likes": 14200,
        "comments": 740,
        "contact_type": "dm",
        "contact": "https://www.tiktok.com/@creator_b",
    },
    Platform.instagram: {
        "handle": "@creator_c",
        "display_name": "Creator C",
        "profile_url": "https://www.instagram.com/creator_c/",
        "follower_count": 275000,
        "bio": "Beauty creator focused on skincare carousels and reels.",
        "content_url": "https://www.instagram.com/reel/creator-c-1/",
        "title": "Sensitive skin favorites",
        "description": "Skincare product picks with usage notes.",
        "views": 72000,
        "likes": 5300,
        "comments": 280,
        "contact_type": "email",
        "contact": "collab@example.com",
    },
}


def _build_candidate(platform: Platform, index: int) -> RawCandidate:
    fixture = _PLATFORM_FIXTURES.get(platform, _PLATFORM_FIXTURES[Platform.youtube])
    suffix = "" if index == 0 else f" {index + 1}"
    handle_suffix = "" if index == 0 else f"_{index + 1}"
    profile_suffix = "" if index == 0 else f"-{index + 1}"
    follower_count = int(fixture["follower_count"]) - (index * 9000)
    views = int(fixture["views"]) - (index * 4500)
    likes = int(fixture["likes"]) - (index * 250)
    comments = int(fixture["comments"]) - (index * 18)
    return RawCandidate(
        platform=platform,
        handle=f"{fixture['handle']}{handle_suffix}",
        display_name=f"{fixture['display_name']}{suffix}",
        profile_url=_variant_url(str(fixture["profile_url"]), profile_suffix),
        follower_count=max(follower_count, 10000),
        bio=str(fixture["bio"]),
        contents=[
            RawContent(
                content_url=_variant_url(str(fixture["content_url"]), profile_suffix),
                title=f"{fixture['title']}{suffix}",
                description=str(fixture["description"]),
                view_count=max(views, 1000),
                like_count=max(likes, 100),
                comment_count=max(comments, 10),
            )
        ],
        contacts=[
            RawContact(
                contact_type=str(fixture["contact_type"]),
                value=_variant_contact(str(fixture["contact"]), index),
                source_url=_variant_url(str(fixture["profile_url"]), profile_suffix),
            )
        ],
    )


def _variant_url(url: str, suffix: str) -> str:
    if not suffix:
        return url
    if url.endswith("/"):
        return f"{url.rstrip('/')}{suffix}/"
    return f"{url}{suffix}"


def _variant_contact(contact: str, index: int) -> str:
    if index == 0:
        return contact
    if "@" in contact and not contact.startswith("http"):
        local, domain = contact.split("@", 1)
        return f"{local}+{index + 1}@{domain}"
    return _variant_url(contact, f"-{index + 1}")
