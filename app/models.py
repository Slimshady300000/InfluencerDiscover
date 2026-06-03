from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Platform(StrEnum):
    youtube = "youtube"
    tiktok = "tiktok"
    instagram = "instagram"
    web = "web"


class TaskStatus(StrEnum):
    queued = "queued"
    running = "running"
    complete = "complete"
    failed = "failed"


class Creator(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    display_name: str
    primary_topics: str = ""
    language: str = ""
    region_hint: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    accounts: list["PlatformAccount"] = Relationship(back_populates="creator")
    contacts: list["ContactRecord"] = Relationship(back_populates="creator")
    follow_ups: list["FollowUp"] = Relationship(back_populates="creator")


class PlatformAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    creator_id: Optional[int] = Field(default=None, foreign_key="creator.id")
    platform: Platform
    handle: str
    profile_url: str
    follower_count: int = 0
    bio: str = ""
    avatar_url: str = ""
    last_refreshed_at: Optional[datetime] = None

    creator: Creator = Relationship(back_populates="accounts")
    content_samples: list["ContentSample"] = Relationship(back_populates="account")


class ContentSample(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: Optional[int] = Field(default=None, foreign_key="platformaccount.id")
    content_url: str
    title: str = ""
    description: str = ""
    hashtags: str = ""
    posted_at: Optional[datetime] = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    language: str = ""
    translated_summary: str = ""

    account: PlatformAccount = Relationship(back_populates="content_samples")


class ContactRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    creator_id: Optional[int] = Field(default=None, foreign_key="creator.id")
    contact_type: str
    value: str
    source_url: str
    confidence: float = 1.0
    is_public: bool = True
    last_verified_at: Optional[datetime] = None

    creator: Creator = Relationship(back_populates="contacts")


class SearchTask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    input_text: str
    input_type: str
    platforms: str
    language_options: str = ""
    status: TaskStatus = TaskStatus.queued
    error_summary: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    results: list["ScoreResult"] = Relationship(back_populates="task")


class ScoreResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: Optional[int] = Field(default=None, foreign_key="searchtask.id")
    creator_id: Optional[int] = Field(default=None, foreign_key="creator.id")
    platform_account_id: Optional[int] = Field(default=None, foreign_key="platformaccount.id")
    normalized_views: float = 0.0
    normalized_engagement: float = 0.0
    normalized_followers: float = 0.0
    topic_score: float = 0.0
    data_performance_score: float = 0.0
    contactability_score: float = 0.0
    final_score: float = 0.0
    reasons: str = ""
    risks: str = ""

    task: SearchTask = Relationship(back_populates="results")


class FollowUp(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    creator_id: Optional[int] = Field(default=None, foreign_key="creator.id")
    owner: str = ""
    status: str = "待审核"
    tags: str = ""
    notes: str = ""
    updated_at: datetime = Field(default_factory=utc_now)

    creator: Creator = Relationship(back_populates="follow_ups")
