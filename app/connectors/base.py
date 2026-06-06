from dataclasses import dataclass, field
from typing import Protocol

from app.models import Platform
from app.services.query_parser import SearchIntent


@dataclass(frozen=True)
class RawContent:
    content_url: str
    title: str
    description: str = ""
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    hashtags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RawContact:
    contact_type: str
    value: str
    source_url: str
    is_public: bool = True


@dataclass(frozen=True)
class RawCandidate:
    platform: Platform
    handle: str
    display_name: str
    profile_url: str
    follower_count: int
    bio: str = ""
    avatar_url: str = ""
    contents: list[RawContent] = field(default_factory=list)
    contacts: list[RawContact] = field(default_factory=list)


class CandidateConnector(Protocol):
    name: str

    def search(self, intent: SearchIntent) -> list[RawCandidate]:
        """Return raw candidates from this source."""
