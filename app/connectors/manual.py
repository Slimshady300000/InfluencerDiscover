from app.connectors.base import RawCandidate, RawContact, RawContent
from app.models import Platform
from app.services.query_parser import SearchIntent


class ManualConnector:
    name = "manual"

    def search(self, intent: SearchIntent) -> list[RawCandidate]:
        platform = intent.platforms[0] if intent.platforms else Platform.youtube
        return [
            RawCandidate(
                platform=platform,
                handle="@creator_a",
                display_name="Creator A",
                profile_url=f"https://example.com/{platform.value}/creator_a",
                follower_count=310000,
                bio="Skincare reviews and beauty routines.",
                contents=[
                    RawContent(
                        content_url="https://example.com/video/1",
                        title="Hydrating serum review",
                        description="Skincare serum test for sensitive skin.",
                        view_count=96000,
                        like_count=6100,
                        comment_count=320,
                    )
                ],
                contacts=[
                    RawContact(
                        contact_type="email",
                        value="business@example.com",
                        source_url=f"https://example.com/{platform.value}/creator_a",
                    )
                ],
            )
        ]
