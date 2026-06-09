from app.connectors.base import RawCandidate, RawContact, RawContent
from app.models import Platform
from app.services.query_parser import SearchIntent


class ManualConnector:
    name = "manual"

    def search(self, intent: SearchIntent) -> list[RawCandidate]:
        platforms = intent.platforms or [Platform.youtube]
        return [_build_candidate(platform) for platform in platforms]


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


def _build_candidate(platform: Platform) -> RawCandidate:
    fixture = _PLATFORM_FIXTURES.get(platform, _PLATFORM_FIXTURES[Platform.youtube])
    return RawCandidate(
        platform=platform,
        handle=str(fixture["handle"]),
        display_name=str(fixture["display_name"]),
        profile_url=str(fixture["profile_url"]),
        follower_count=int(fixture["follower_count"]),
        bio=str(fixture["bio"]),
        contents=[
            RawContent(
                content_url=str(fixture["content_url"]),
                title=str(fixture["title"]),
                description=str(fixture["description"]),
                view_count=int(fixture["views"]),
                like_count=int(fixture["likes"]),
                comment_count=int(fixture["comments"]),
            )
        ],
        contacts=[
            RawContact(
                contact_type=str(fixture["contact_type"]),
                value=str(fixture["contact"]),
                source_url=str(fixture["profile_url"]),
            )
        ],
    )
