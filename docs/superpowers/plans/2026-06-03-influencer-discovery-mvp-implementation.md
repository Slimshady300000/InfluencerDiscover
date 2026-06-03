# Influencer Discovery MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a usable internal MVP that lets managers search, score, review, track, and export TikTok/YouTube/Instagram creator candidates.

**Architecture:** Use a Python web app with server-rendered pages for speed, a focused service layer for scoring and analysis, and connector interfaces so real data sources can be added incrementally. Start with manual/mock data and YouTube/search connectors, then add conservative TikTok/Instagram link enrichment without making the app depend on hard-to-approve APIs.

**Tech Stack:** Python 3.12, FastAPI, Jinja2, HTMX, SQLModel, SQLite, RQ, Redis, httpx, openpyxl, pytest, Playwright for UI verification, Docker Compose for local deployment.

---

## File Structure

Create this project structure under `D:\Influencer_Discovery`:

```text
app/
  __init__.py
  main.py
  config.py
  db.py
  models.py
  schemas.py
  connectors/
    __init__.py
    base.py
    manual.py
    search_engine.py
    youtube.py
  jobs/
    __init__.py
    queue.py
    worker.py
  services/
    __init__.py
    analysis.py
    due_diligence.py
    exporter.py
    query_parser.py
    scoring.py
    search_runner.py
  web/
    __init__.py
    routes.py
  templates/
    layout.html
    search.html
    task_detail.html
    creator_detail.html
    card.html
  static/
    app.css
tests/
  conftest.py
  test_models.py
  test_query_parser.py
  test_scoring.py
  test_search_runner.py
  test_exporter.py
  test_web.py
docs/
  superpowers/
    plans/
      2026-06-03-influencer-discovery-mvp-implementation.md
.env.example
.gitignore
docker-compose.yml
pyproject.toml
README.md
```

Responsibility boundaries:

- `app/models.py`: database tables only.
- `app/schemas.py`: Pydantic request/response DTOs only.
- `app/connectors/*`: source-specific candidate discovery and enrichment only.
- `app/services/query_parser.py`: parse user inputs into search intent.
- `app/services/scoring.py`: deterministic scoring and normalization only.
- `app/services/search_runner.py`: orchestrate connectors, persistence, scoring, and task status.
- `app/services/analysis.py`: multilingual expansion, language hints, and content summary text.
- `app/services/due_diligence.py`: generate manager review cards from stored data.
- `app/services/exporter.py`: Excel export only.
- `app/web/routes.py`: HTTP routes and template rendering only.

## Task 1: Project Skeleton And Dependency Setup

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `README.md`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/config.py`
- Test: `tests/test_web.py`

- [ ] **Step 1: Create the failing smoke test**

Create `tests/test_web.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_homepage_returns_search_screen():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Influencer Discovery" in response.text
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```powershell
python -m pytest tests/test_web.py -q
```

Expected: FAIL because `app.main` does not exist.

- [ ] **Step 3: Create dependency metadata**

Create `pyproject.toml`:

```toml
[project]
name = "influencer-discovery"
version = "0.1.0"
description = "Internal influencer discovery MVP"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "jinja2>=3.1",
  "python-multipart>=0.0.9",
  "sqlmodel>=0.0.22",
  "pydantic-settings>=2.4",
  "httpx>=0.27",
  "rq>=1.16",
  "redis>=5.0",
  "openpyxl>=3.1",
  "beautifulsoup4>=4.12",
  "rapidfuzz>=3.9",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2",
  "pytest-cov>=5.0",
  "ruff>=0.6",
]

[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 100
target-version = "py312"
```

Create `.env.example`:

```text
APP_NAME=Influencer Discovery
DATABASE_URL=sqlite:///./data/influencer_discovery.db
REDIS_URL=redis://localhost:6379/0
YOUTUBE_API_KEY=
SEARCH_ENGINE_API_KEY=
SEARCH_ENGINE_ID=
```

Create `.gitignore`:

```text
__pycache__/
*.pyc
.venv/
.env
data/
.pytest_cache/
.ruff_cache/
.playwright-cli/
.superpowers/
```

Create `README.md`:

```markdown
# Influencer Discovery

Internal MVP for finding, scoring, reviewing, and exporting overseas influencer candidates.

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
uvicorn app.main:app --reload
```
```

- [ ] **Step 4: Create minimal app configuration and route**

Create `app/__init__.py`:

```python
"""Influencer Discovery MVP package."""
```

Create `app/config.py`:

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Influencer Discovery"
    database_url: str = "sqlite:///./data/influencer_discovery.db"
    redis_url: str = "redis://localhost:6379/0"
    youtube_api_key: str = ""
    search_engine_api_key: str = ""
    search_engine_id: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Create `app/main.py`:

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name)


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return "<h1>Influencer Discovery</h1><p>Search creator candidates.</p>"
```

- [ ] **Step 5: Run the smoke test**

Run:

```powershell
python -m pytest tests/test_web.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add pyproject.toml .env.example .gitignore README.md app tests
git commit -m "chore: scaffold influencer discovery app"
```

## Task 2: Database Models And Session Helpers

**Files:**
- Create: `app/db.py`
- Create: `app/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write model tests**

Create `tests/test_models.py`:

```python
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import ContactRecord, Creator, Platform, PlatformAccount, SearchTask, TaskStatus


def test_creator_platform_account_and_contact_persist():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        task = SearchTask(
            input_text="skincare",
            input_type="keyword",
            platforms="youtube,tiktok,instagram",
            status=TaskStatus.queued,
        )
        creator = Creator(display_name="Creator A", primary_topics="skincare,beauty")
        account = PlatformAccount(
            creator=creator,
            platform=Platform.youtube,
            handle="@creator_a",
            profile_url="https://youtube.com/@creator_a",
            follower_count=310000,
        )
        contact = ContactRecord(
            creator=creator,
            contact_type="email",
            value="biz@example.com",
            source_url="https://youtube.com/@creator_a/about",
            is_public=True,
        )
        session.add(task)
        session.add(account)
        session.add(contact)
        session.commit()

        saved = session.exec(select(Creator)).one()
        assert saved.display_name == "Creator A"
        assert saved.accounts[0].platform == Platform.youtube
        assert saved.contacts[0].value == "biz@example.com"
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```powershell
python -m pytest tests/test_models.py -q
```

Expected: FAIL because `app.models` does not exist.

- [ ] **Step 3: Implement models**

Create `app/models.py`:

```python
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
```

- [ ] **Step 4: Implement DB helpers**

Create `app/db.py`:

```python
from pathlib import Path
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings


def build_engine():
    settings = get_settings()
    if settings.database_url.startswith("sqlite:///./data/"):
        Path("data").mkdir(exist_ok=True)
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    return create_engine(settings.database_url, connect_args=connect_args)


engine = build_engine()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
```

- [ ] **Step 5: Run model tests**

Run:

```powershell
python -m pytest tests/test_models.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add app/db.py app/models.py tests/test_models.py
git commit -m "feat: add database models"
```

## Task 3: Query Parser And Multilingual Search Intent

**Files:**
- Create: `app/services/query_parser.py`
- Test: `tests/test_query_parser.py`

- [ ] **Step 1: Write parser tests**

Create `tests/test_query_parser.py`:

```python
from app.models import Platform
from app.services.query_parser import InputType, parse_search_input


def test_parse_keyword_input():
    intent = parse_search_input("skincare", [Platform.youtube])
    assert intent.input_type == InputType.keyword
    assert intent.core_terms == ["skincare"]
    assert intent.platforms == [Platform.youtube]


def test_parse_brief_input_expands_terms():
    text = "Southeast Asia beauty brief for skincare serum"
    intent = parse_search_input(text, [Platform.tiktok, Platform.instagram])
    assert intent.input_type == InputType.brief
    assert "beauty" in intent.core_terms
    assert "skincare" in intent.expanded_terms


def test_parse_seed_url():
    intent = parse_search_input("https://www.youtube.com/@creator_a", [Platform.youtube])
    assert intent.input_type == InputType.seed_url
    assert intent.seed_urls == ["https://www.youtube.com/@creator_a"]
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_query_parser.py -q
```

Expected: FAIL because `app.services.query_parser` does not exist.

- [ ] **Step 3: Implement parser**

Create `app/services/__init__.py`:

```python
"""Service layer for influencer discovery."""
```

Create `app/services/query_parser.py`:

```python
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
```

- [ ] **Step 4: Run parser tests**

Run:

```powershell
python -m pytest tests/test_query_parser.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add app/services tests/test_query_parser.py
git commit -m "feat: parse creator search inputs"
```

## Task 4: Scoring Service

**Files:**
- Create: `app/services/scoring.py`
- Test: `tests/test_scoring.py`

- [ ] **Step 1: Write scoring tests**

Create `tests/test_scoring.py`:

```python
from app.services.scoring import CandidateMetrics, score_batch


def test_score_batch_ranks_data_performance_first():
    candidates = [
        CandidateMetrics(
            key="low",
            platform="youtube",
            follower_count=10000,
            recent_view_count=1000,
            engagement_rate=0.02,
            topic_score=0.95,
            has_public_contact=True,
            has_dm_entry=True,
        ),
        CandidateMetrics(
            key="high",
            platform="youtube",
            follower_count=400000,
            recent_view_count=120000,
            engagement_rate=0.08,
            topic_score=0.75,
            has_public_contact=False,
            has_dm_entry=True,
        ),
    ]
    scored = score_batch(candidates)
    assert scored[0].key == "high"
    assert scored[0].final_score > scored[1].final_score


def test_score_batch_filters_low_topic_match():
    candidates = [
        CandidateMetrics(
            key="off-topic",
            platform="tiktok",
            follower_count=900000,
            recent_view_count=600000,
            engagement_rate=0.12,
            topic_score=0.10,
            has_public_contact=True,
            has_dm_entry=True,
        )
    ]
    scored = score_batch(candidates, minimum_topic_score=0.2)
    assert scored == []
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_scoring.py -q
```

Expected: FAIL because `app.services.scoring` does not exist.

- [ ] **Step 3: Implement scoring**

Create `app/services/scoring.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateMetrics:
    key: str
    platform: str
    follower_count: int
    recent_view_count: int
    engagement_rate: float
    topic_score: float
    has_public_contact: bool
    has_dm_entry: bool


@dataclass(frozen=True)
class ScoredCandidate:
    key: str
    platform: str
    normalized_views: float
    normalized_engagement: float
    normalized_followers: float
    topic_score: float
    data_performance_score: float
    contactability_score: float
    final_score: float
    reasons: list[str]
    risks: list[str]


def score_batch(
    candidates: list[CandidateMetrics],
    minimum_topic_score: float = 0.2,
) -> list[ScoredCandidate]:
    eligible = [candidate for candidate in candidates if candidate.topic_score >= minimum_topic_score]
    if not eligible:
        return []
    scored: list[ScoredCandidate] = []
    for platform in sorted({candidate.platform for candidate in eligible}):
        platform_candidates = [candidate for candidate in eligible if candidate.platform == platform]
        max_views = max(candidate.recent_view_count for candidate in platform_candidates) or 1
        max_engagement = max(candidate.engagement_rate for candidate in platform_candidates) or 1
        max_followers = max(candidate.follower_count for candidate in platform_candidates) or 1
        for candidate in platform_candidates:
            normalized_views = candidate.recent_view_count / max_views
            normalized_engagement = candidate.engagement_rate / max_engagement
            normalized_followers = candidate.follower_count / max_followers
            data_score = (
                normalized_views * 0.35
                + normalized_engagement * 0.25
                + normalized_followers * 0.15
            ) / 0.75
            contact_score = 1.0 if candidate.has_public_contact else 0.5 if candidate.has_dm_entry else 0.0
            final_score = (
                data_score * 75.0
                + candidate.topic_score * 15.0
                + contact_score * 10.0
            )
            risks = []
            if candidate.topic_score < 0.45:
                risks.append("Topic match is weak and needs manager review.")
            if not candidate.has_public_contact:
                risks.append("No public business contact found.")
            scored.append(
                ScoredCandidate(
                    key=candidate.key,
                    platform=candidate.platform,
                    normalized_views=normalized_views,
                    normalized_engagement=normalized_engagement,
                    normalized_followers=normalized_followers,
                    topic_score=candidate.topic_score,
                    data_performance_score=data_score,
                    contactability_score=contact_score,
                    final_score=round(final_score, 2),
                    reasons=[
                        "Ranked mainly by recent views, engagement rate, and follower count.",
                        "Compared within the same platform batch.",
                    ],
                    risks=risks,
                )
            )
    return sorted(scored, key=lambda item: item.final_score, reverse=True)
```

- [ ] **Step 4: Run scoring tests**

Run:

```powershell
python -m pytest tests/test_scoring.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add app/services/scoring.py tests/test_scoring.py
git commit -m "feat: score influencer candidates"
```

## Task 5: Connector Interfaces And Manual Connector

**Files:**
- Create: `app/connectors/__init__.py`
- Create: `app/connectors/base.py`
- Create: `app/connectors/manual.py`
- Test: `tests/test_search_runner.py`

- [ ] **Step 1: Write connector contract test**

Create `tests/test_search_runner.py`:

```python
from app.connectors.manual import ManualConnector
from app.models import Platform
from app.services.query_parser import parse_search_input


def test_manual_connector_returns_candidates():
    intent = parse_search_input("skincare", [Platform.youtube])
    connector = ManualConnector()
    candidates = connector.search(intent)
    assert candidates
    assert candidates[0].platform == Platform.youtube
    assert candidates[0].handle.startswith("@")
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m pytest tests/test_search_runner.py -q
```

Expected: FAIL because connector files do not exist.

- [ ] **Step 3: Implement connector interface**

Create `app/connectors/__init__.py`:

```python
"""Data source connectors."""
```

Create `app/connectors/base.py`:

```python
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
```

- [ ] **Step 4: Implement manual connector**

Create `app/connectors/manual.py`:

```python
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
```

- [ ] **Step 5: Run connector test**

Run:

```powershell
python -m pytest tests/test_search_runner.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add app/connectors tests/test_search_runner.py
git commit -m "feat: add candidate connector contract"
```

## Task 6: Search Runner Persistence And Scoring Integration

**Files:**
- Create: `app/services/search_runner.py`
- Modify: `tests/test_search_runner.py`

- [ ] **Step 1: Add search runner test**

Append to `tests/test_search_runner.py`:

```python
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Creator, SearchTask, TaskStatus
from app.services.search_runner import run_search_task


def test_run_search_task_persists_candidates_and_scores():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        task = SearchTask(
            input_text="skincare",
            input_type="keyword",
            platforms="youtube",
            status=TaskStatus.queued,
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        run_search_task(session, task.id)

        saved_task = session.get(SearchTask, task.id)
        creators = session.exec(select(Creator)).all()
        assert saved_task.status == TaskStatus.complete
        assert len(creators) == 1
        assert saved_task.results[0].final_score > 0
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m pytest tests/test_search_runner.py -q
```

Expected: FAIL because `run_search_task` does not exist.

- [ ] **Step 3: Implement search runner**

Create `app/services/search_runner.py`:

```python
from statistics import mean

from sqlmodel import Session

from app.connectors.base import RawCandidate
from app.connectors.manual import ManualConnector
from app.models import (
    ContactRecord,
    ContentSample,
    Creator,
    Platform,
    PlatformAccount,
    ScoreResult,
    SearchTask,
    TaskStatus,
)
from app.services.query_parser import parse_search_input
from app.services.scoring import CandidateMetrics, score_batch


def run_search_task(session: Session, task_id: int) -> None:
    task = session.get(SearchTask, task_id)
    if task is None:
        raise ValueError(f"Search task not found: {task_id}")
    task.status = TaskStatus.running
    session.add(task)
    session.commit()

    try:
        platforms = [Platform(value) for value in task.platforms.split(",") if value]
        intent = parse_search_input(task.input_text, platforms)
        raw_candidates = ManualConnector().search(intent)
        persisted = [_persist_candidate(session, candidate) for candidate in raw_candidates]
        metrics = [
            _metrics_for_candidate(candidate, creator_id, account_id)
            for candidate, creator_id, account_id in persisted
        ]
        scored = score_batch(metrics)
        for scored_candidate in scored:
            creator_id, account_id = [int(part) for part in scored_candidate.key.split(":")]
            session.add(
                ScoreResult(
                    task_id=task.id,
                    creator_id=creator_id,
                    platform_account_id=account_id,
                    normalized_views=scored_candidate.normalized_views,
                    normalized_engagement=scored_candidate.normalized_engagement,
                    normalized_followers=scored_candidate.normalized_followers,
                    topic_score=scored_candidate.topic_score,
                    data_performance_score=scored_candidate.data_performance_score,
                    contactability_score=scored_candidate.contactability_score,
                    final_score=scored_candidate.final_score,
                    reasons=" | ".join(scored_candidate.reasons),
                    risks=" | ".join(scored_candidate.risks),
                )
            )
        task.status = TaskStatus.complete
        task.error_summary = ""
        session.add(task)
        session.commit()
    except Exception as exc:
        task.status = TaskStatus.failed
        task.error_summary = str(exc)
        session.add(task)
        session.commit()
        raise


def _persist_candidate(session: Session, candidate: RawCandidate) -> tuple[RawCandidate, int, int]:
    creator = Creator(display_name=candidate.display_name, primary_topics=candidate.bio)
    account = PlatformAccount(
        creator=creator,
        platform=candidate.platform,
        handle=candidate.handle,
        profile_url=candidate.profile_url,
        follower_count=candidate.follower_count,
        bio=candidate.bio,
        avatar_url=candidate.avatar_url,
    )
    session.add(account)
    session.commit()
    session.refresh(creator)
    session.refresh(account)
    for content in candidate.contents:
        session.add(
            ContentSample(
                account_id=account.id,
                content_url=content.content_url,
                title=content.title,
                description=content.description,
                hashtags=",".join(content.hashtags),
                view_count=content.view_count,
                like_count=content.like_count,
                comment_count=content.comment_count,
                share_count=content.share_count,
            )
        )
    for contact in candidate.contacts:
        session.add(
            ContactRecord(
                creator_id=creator.id,
                contact_type=contact.contact_type,
                value=contact.value,
                source_url=contact.source_url,
                is_public=contact.is_public,
            )
        )
    session.commit()
    return candidate, creator.id, account.id


def _metrics_for_candidate(candidate: RawCandidate, creator_id: int, account_id: int) -> CandidateMetrics:
    views = [content.view_count for content in candidate.contents]
    likes = sum(content.like_count for content in candidate.contents)
    comments = sum(content.comment_count for content in candidate.contents)
    average_views = int(mean(views)) if views else 0
    engagement_rate = (likes + comments) / max(sum(views), 1)
    has_public_contact = any(contact.is_public for contact in candidate.contacts)
    has_dm_entry = candidate.platform in {Platform.tiktok, Platform.instagram}
    topic_score = 0.8 if "skincare" in (candidate.bio + " " + candidate.display_name).lower() else 0.4
    return CandidateMetrics(
        key=f"{creator_id}:{account_id}",
        platform=candidate.platform.value,
        follower_count=candidate.follower_count,
        recent_view_count=average_views,
        engagement_rate=engagement_rate,
        topic_score=topic_score,
        has_public_contact=has_public_contact,
        has_dm_entry=has_dm_entry,
    )
```

- [ ] **Step 4: Run search runner tests**

Run:

```powershell
python -m pytest tests/test_search_runner.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add app/services/search_runner.py tests/test_search_runner.py
git commit -m "feat: persist and score search results"
```

## Task 7: Web UI With Search, Results, And Follow-Up State

**Files:**
- Modify: `app/main.py`
- Create: `app/web/__init__.py`
- Create: `app/web/routes.py`
- Create: `app/templates/layout.html`
- Create: `app/templates/search.html`
- Create: `app/templates/task_detail.html`
- Create: `app/templates/creator_detail.html`
- Create: `app/static/app.css`
- Modify: `tests/test_web.py`

- [ ] **Step 1: Add web workflow tests**

Replace `tests/test_web.py` with:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_homepage_returns_search_screen():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Influencer Discovery" in response.text
    assert "Start Search" in response.text


def test_create_search_task_redirects_to_task_page():
    client = TestClient(app)
    response = client.post(
        "/search",
        data={"input_text": "skincare", "platforms": ["youtube"]},
        follow_redirects=False,
    )
    assert response.status_code in {302, 303}
    assert "/tasks/" in response.headers["location"]
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_web.py -q
```

Expected: FAIL because `/search` is not implemented.

- [ ] **Step 3: Implement web routes**

Create `app/web/__init__.py`:

```python
"""Web route package."""
```

Create `app/web/routes.py`:

```python
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db import get_session
from app.models import SearchTask, TaskStatus
from app.services.search_runner import run_search_task

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def search_page(request: Request, session: Session = Depends(get_session)):
    tasks = session.exec(select(SearchTask).order_by(SearchTask.created_at.desc())).all()
    return templates.TemplateResponse("search.html", {"request": request, "tasks": tasks})


@router.post("/search")
def create_search_task(
    input_text: str = Form(min_length=1),
    platforms: list[str] = Form(default=["youtube"]),
    session: Session = Depends(get_session),
):
    task = SearchTask(
        input_text=input_text,
        input_type="keyword",
        platforms=",".join(platforms),
        status=TaskStatus.queued,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    run_search_task(session, task.id)
    return RedirectResponse(url=f"/tasks/{task.id}", status_code=303)


@router.get("/tasks/{task_id}")
def task_detail(task_id: int, request: Request, session: Session = Depends(get_session)):
    task = session.get(SearchTask, task_id)
    return templates.TemplateResponse("task_detail.html", {"request": request, "task": task})
```

Modify `app/main.py`:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import init_db
from app.web.routes import router

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    init_db()
```

- [ ] **Step 4: Create templates and CSS**

Create `app/templates/layout.html`:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Influencer Discovery</title>
  <link rel="stylesheet" href="/static/app.css">
</head>
<body>
  <header class="topbar">
    <strong>Influencer Discovery</strong>
    <nav><a href="/">Search</a></nav>
  </header>
  <main class="page">{% block content %}{% endblock %}</main>
</body>
</html>
```

Create `app/templates/search.html`:

```html
{% extends "layout.html" %}
{% block content %}
<section class="panel">
  <h1>Search creator candidates</h1>
  <form method="post" action="/search" class="search-form">
    <input name="input_text" required aria-label="Keyword, brand brief, or seed creator URL">
    <label><input type="checkbox" name="platforms" value="youtube" checked> YouTube</label>
    <label><input type="checkbox" name="platforms" value="tiktok"> TikTok</label>
    <label><input type="checkbox" name="platforms" value="instagram"> Instagram</label>
    <button type="submit">Start Search</button>
  </form>
</section>
<section class="panel">
  <h2>Recent tasks</h2>
  <table>
    <tr><th>ID</th><th>Input</th><th>Status</th></tr>
    {% for task in tasks %}
      <tr><td><a href="/tasks/{{ task.id }}">{{ task.id }}</a></td><td>{{ task.input_text }}</td><td>{{ task.status }}</td></tr>
    {% endfor %}
  </table>
</section>
{% endblock %}
```

Create `app/templates/task_detail.html`:

```html
{% extends "layout.html" %}
{% block content %}
<section class="panel">
  <h1>Search task #{{ task.id }}</h1>
  <p>Status: {{ task.status }}</p>
  <p>Input: {{ task.input_text }}</p>
  <table>
    <tr><th>Creator ID</th><th>Score</th><th>Reasons</th><th>Risks</th></tr>
    {% for result in task.results %}
      <tr>
        <td>{{ result.creator_id }}</td>
        <td>{{ result.final_score }}</td>
        <td>{{ result.reasons }}</td>
        <td>{{ result.risks }}</td>
      </tr>
    {% endfor %}
  </table>
</section>
{% endblock %}
```

Create `app/templates/creator_detail.html`:

```html
{% extends "layout.html" %}
{% block content %}
<section class="panel">
  <h1>{{ creator.display_name }}</h1>
  <p>{{ creator.primary_topics }}</p>
</section>
{% endblock %}
```

Create `app/static/app.css`:

```css
body { margin: 0; font-family: Arial, sans-serif; background: #f6f7f9; color: #1f2933; }
.topbar { display: flex; gap: 24px; align-items: center; padding: 16px 24px; background: #fff; border-bottom: 1px solid #dce3ea; }
.page { max-width: 1180px; margin: 0 auto; padding: 24px; }
.panel { background: #fff; border: 1px solid #dce3ea; border-radius: 8px; padding: 18px; margin-bottom: 18px; }
.search-form { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
input[type="text"], input[name="input_text"] { min-width: 420px; padding: 10px; border: 1px solid #cbd5df; border-radius: 6px; }
button { padding: 10px 14px; border: 1px solid #b8c4cf; border-radius: 6px; background: #f8fafc; font-weight: 700; }
table { width: 100%; border-collapse: collapse; }
th, td { border-bottom: 1px solid #e4e9ee; padding: 10px; text-align: left; }
```

- [ ] **Step 5: Run web tests**

Run:

```powershell
python -m pytest tests/test_web.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add app/main.py app/web app/templates app/static tests/test_web.py
git commit -m "feat: add internal search web UI"
```

## Task 8: Excel Export

**Files:**
- Create: `app/services/exporter.py`
- Modify: `app/web/routes.py`
- Test: `tests/test_exporter.py`

- [ ] **Step 1: Write export test**

Create `tests/test_exporter.py`:

```python
from io import BytesIO

from openpyxl import load_workbook

from app.services.exporter import build_candidate_workbook


def test_build_candidate_workbook_contains_expected_headers():
    data = [
        {
            "creator": "Creator A",
            "platform": "YouTube",
            "followers": 310000,
            "recent_views": 96000,
            "engagement_rate": 0.071,
            "score": 87.0,
            "contact": "business@example.com",
        }
    ]
    payload = build_candidate_workbook(data)
    workbook = load_workbook(BytesIO(payload))
    sheet = workbook.active
    assert sheet["A1"].value == "Creator"
    assert sheet["G2"].value == "business@example.com"
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m pytest tests/test_exporter.py -q
```

Expected: FAIL because `app.services.exporter` does not exist.

- [ ] **Step 3: Implement exporter**

Create `app/services/exporter.py`:

```python
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font


def build_candidate_workbook(rows: list[dict]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Candidates"
    headers = ["Creator", "Platform", "Followers", "Recent Views", "Engagement Rate", "Score", "Contact"]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in rows:
        sheet.append(
            [
                row["creator"],
                row["platform"],
                row["followers"],
                row["recent_views"],
                row["engagement_rate"],
                row["score"],
                row["contact"],
            ]
        )
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
```

- [ ] **Step 4: Add export route**

Update the top imports in `app/web/routes.py`:

```python
from fastapi.responses import RedirectResponse, Response
from app.models import Creator, PlatformAccount, SearchTask, TaskStatus
from app.services.exporter import build_candidate_workbook
```

Add this route below `task_detail` in `app/web/routes.py`:

```python

@router.get("/tasks/{task_id}/export.xlsx")
def export_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(SearchTask, task_id)
    rows = []
    for result in task.results:
        creator = session.get(Creator, result.creator_id)
        account = session.get(PlatformAccount, result.platform_account_id)
        contact = creator.contacts[0].value if creator and creator.contacts else ""
        rows.append(
            {
                "creator": creator.display_name if creator else "",
                "platform": account.platform.value if account else "",
                "followers": account.follower_count if account else 0,
                "recent_views": 0,
                "engagement_rate": result.normalized_engagement,
                "score": result.final_score,
                "contact": contact,
            }
        )
    payload = build_candidate_workbook(rows)
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="task-{task_id}-candidates.xlsx"'},
    )
```

- [ ] **Step 5: Run export tests**

Run:

```powershell
python -m pytest tests/test_exporter.py -q
```

Expected: PASS.

- [ ] **Step 6: Run full test suite**

Run:

```powershell
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
git add app/services/exporter.py app/web/routes.py tests/test_exporter.py
git commit -m "feat: export candidate lists to excel"
```

## Task 9: Due Diligence Card Generation

**Files:**
- Create: `app/services/due_diligence.py`
- Create: `app/templates/card.html`
- Modify: `app/web/routes.py`
- Test: `tests/test_due_diligence.py`

- [ ] **Step 1: Write card generation test**

Create `tests/test_due_diligence.py`:

```python
from app.services.due_diligence import build_due_diligence_card


def test_build_due_diligence_card_includes_recommendation_and_risk():
    card = build_due_diligence_card(
        creator_name="Creator A",
        platform="YouTube",
        follower_count=310000,
        score=87.0,
        content_titles=["Hydrating serum review", "Sensitive skin routine"],
        contact="business@example.com",
        risks=["No recent sponsored content found."],
    )
    assert "Creator A" in card.recommendation
    assert "Hydrating serum review" in card.representative_content
    assert card.suggested_contact == "business@example.com"
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m pytest tests/test_due_diligence.py -q
```

Expected: FAIL because `app.services.due_diligence` does not exist.

- [ ] **Step 3: Implement card service**

Create `app/services/due_diligence.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class DueDiligenceCard:
    creator_name: str
    recommendation: str
    representative_content: str
    data_highlights: str
    risks: str
    suggested_contact: str


def build_due_diligence_card(
    creator_name: str,
    platform: str,
    follower_count: int,
    score: float,
    content_titles: list[str],
    contact: str,
    risks: list[str],
) -> DueDiligenceCard:
    representative_content = " | ".join(content_titles[:5]) if content_titles else "No recent content samples stored."
    risk_text = " | ".join(risks) if risks else "No obvious risk found in stored data."
    recommendation = (
        f"{creator_name} is recommended for manager review because the {platform} account "
        f"has a score of {score:.1f} and {follower_count:,} followers."
    )
    return DueDiligenceCard(
        creator_name=creator_name,
        recommendation=recommendation,
        representative_content=representative_content,
        data_highlights=f"Followers: {follower_count:,}. Score: {score:.1f}.",
        risks=risk_text,
        suggested_contact=contact or "Use public DM entry if visible on the profile.",
    )
```

- [ ] **Step 4: Create card template and route**

Create `app/templates/card.html`:

```html
{% extends "layout.html" %}
{% block content %}
<section class="panel">
  <h1>{{ card.creator_name }}</h1>
  <p><strong>Recommendation:</strong> {{ card.recommendation }}</p>
  <p><strong>Representative content:</strong> {{ card.representative_content }}</p>
  <p><strong>Data highlights:</strong> {{ card.data_highlights }}</p>
  <p><strong>Risks:</strong> {{ card.risks }}</p>
  <p><strong>Suggested contact:</strong> {{ card.suggested_contact }}</p>
</section>
{% endblock %}
```

Update the top imports in `app/web/routes.py`:

```python
from app.models import Creator, PlatformAccount, ScoreResult, SearchTask, TaskStatus
from app.services.due_diligence import build_due_diligence_card
```

Add this route below `export_task` in `app/web/routes.py`:

```python

@router.get("/results/{result_id}/card")
def result_card(result_id: int, request: Request, session: Session = Depends(get_session)):
    result = session.get(ScoreResult, result_id)
    creator = session.get(Creator, result.creator_id)
    account = session.get(PlatformAccount, result.platform_account_id)
    titles = [sample.title for sample in account.content_samples] if account else []
    contact = creator.contacts[0].value if creator and creator.contacts else ""
    card = build_due_diligence_card(
        creator_name=creator.display_name,
        platform=account.platform.value,
        follower_count=account.follower_count,
        score=result.final_score,
        content_titles=titles,
        contact=contact,
        risks=[result.risks] if result.risks else [],
    )
    return templates.TemplateResponse("card.html", {"request": request, "card": card})
```

- [ ] **Step 5: Run card tests and full suite**

Run:

```powershell
python -m pytest tests/test_due_diligence.py -q
python -m pytest -q
```

Expected: PASS for both commands.

- [ ] **Step 6: Commit**

Run:

```powershell
git add app/services/due_diligence.py app/templates/card.html app/web/routes.py tests/test_due_diligence.py
git commit -m "feat: generate due diligence cards"
```

## Task 10: YouTube Connector

**Files:**
- Create: `app/connectors/youtube.py`
- Test: `tests/test_youtube_connector.py`

- [ ] **Step 1: Write YouTube URL-building test**

Create `tests/test_youtube_connector.py`:

```python
from app.connectors.youtube import YouTubeConnector
from app.models import Platform
from app.services.query_parser import parse_search_input


def test_youtube_connector_builds_search_params():
    connector = YouTubeConnector(api_key="key")
    intent = parse_search_input("skincare", [Platform.youtube])
    params = connector.build_search_params(intent)
    assert params["part"] == "snippet"
    assert params["q"] == "skincare"
    assert params["type"] == "video"
    assert params["key"] == "key"
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m pytest tests/test_youtube_connector.py -q
```

Expected: FAIL because `app.connectors.youtube` does not exist.

- [ ] **Step 3: Implement YouTube connector with dry-run-safe parsing**

Create `app/connectors/youtube.py`:

```python
import httpx

from app.connectors.base import RawCandidate, RawContent
from app.models import Platform
from app.services.query_parser import SearchIntent


class YouTubeConnector:
    name = "youtube"
    search_url = "https://www.googleapis.com/youtube/v3/search"

    def __init__(self, api_key: str, client: httpx.Client | None = None):
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=20)

    def build_search_params(self, intent: SearchIntent) -> dict[str, str | int]:
        query = " ".join(intent.core_terms or intent.expanded_terms)
        return {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 25,
            "key": self.api_key,
        }

    def search(self, intent: SearchIntent) -> list[RawCandidate]:
        if not self.api_key:
            return []
        response = self.client.get(self.search_url, params=self.build_search_params(intent))
        response.raise_for_status()
        payload = response.json()
        candidates: list[RawCandidate] = []
        for item in payload.get("items", []):
            snippet = item.get("snippet", {})
            channel_id = snippet.get("channelId", "")
            channel_title = snippet.get("channelTitle", "Unknown YouTube Creator")
            video_id = item.get("id", {}).get("videoId", "")
            candidates.append(
                RawCandidate(
                    platform=Platform.youtube,
                    handle=channel_title,
                    display_name=channel_title,
                    profile_url=f"https://www.youtube.com/channel/{channel_id}",
                    follower_count=0,
                    bio=snippet.get("description", ""),
                    contents=[
                        RawContent(
                            content_url=f"https://www.youtube.com/watch?v={video_id}",
                            title=snippet.get("title", ""),
                            description=snippet.get("description", ""),
                        )
                    ],
                    contacts=[],
                )
            )
        return candidates
```

- [ ] **Step 4: Run connector tests**

Run:

```powershell
python -m pytest tests/test_youtube_connector.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add app/connectors/youtube.py tests/test_youtube_connector.py
git commit -m "feat: add youtube connector"
```

## Task 11: Search Engine Connector For Cross-Platform Candidate Links

**Files:**
- Create: `app/connectors/search_engine.py`
- Test: `tests/test_search_engine_connector.py`

- [ ] **Step 1: Write search connector test**

Create `tests/test_search_engine_connector.py`:

```python
from app.connectors.search_engine import extract_platform_from_url
from app.models import Platform


def test_extract_platform_from_url():
    assert extract_platform_from_url("https://www.tiktok.com/@creator") == Platform.tiktok
    assert extract_platform_from_url("https://www.instagram.com/creator/") == Platform.instagram
    assert extract_platform_from_url("https://www.youtube.com/@creator") == Platform.youtube
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m pytest tests/test_search_engine_connector.py -q
```

Expected: FAIL because `app.connectors.search_engine` does not exist.

- [ ] **Step 3: Implement URL extraction**

Create `app/connectors/search_engine.py`:

```python
from urllib.parse import urlparse

from app.models import Platform


def extract_platform_from_url(url: str) -> Platform:
    host = urlparse(url).netloc.lower()
    if "tiktok.com" in host:
        return Platform.tiktok
    if "instagram.com" in host:
        return Platform.instagram
    if "youtube.com" in host or "youtu.be" in host:
        return Platform.youtube
    return Platform.web
```

- [ ] **Step 4: Run test**

Run:

```powershell
python -m pytest tests/test_search_engine_connector.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add app/connectors/search_engine.py tests/test_search_engine_connector.py
git commit -m "feat: classify platform links from search"
```

## Task 12: Queue And Worker

**Files:**
- Create: `app/jobs/__init__.py`
- Create: `app/jobs/queue.py`
- Create: `app/jobs/worker.py`
- Modify: `app/web/routes.py`
- Test: `tests/test_queue.py`

- [ ] **Step 1: Write queue configuration test**

Create `tests/test_queue.py`:

```python
from app.jobs.queue import get_queue_name


def test_queue_name_is_stable():
    assert get_queue_name() == "influencer-search"
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m pytest tests/test_queue.py -q
```

Expected: FAIL because `app.jobs.queue` does not exist.

- [ ] **Step 3: Implement queue module**

Create `app/jobs/__init__.py`:

```python
"""Background jobs."""
```

Create `app/jobs/queue.py`:

```python
from redis import Redis
from rq import Queue

from app.config import get_settings


def get_queue_name() -> str:
    return "influencer-search"


def get_queue() -> Queue:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    return Queue(get_queue_name(), connection=redis)
```

Create `app/jobs/worker.py`:

```python
from sqlmodel import Session

from app.db import engine
from app.services.search_runner import run_search_task


def run_search_task_job(task_id: int) -> None:
    with Session(engine) as session:
        run_search_task(session, task_id)
```

- [ ] **Step 4: Change web route to enqueue**

In `app/web/routes.py`, replace direct `run_search_task(session, task.id)` in `create_search_task` with:

```python
    from app.jobs.queue import get_queue
    from app.jobs.worker import run_search_task_job

    get_queue().enqueue(run_search_task_job, task.id)
```

For local development without Redis, add a form field named `run_inline` in `search.html`:

```html
<label><input type="checkbox" name="run_inline" value="yes" checked> Run inline for local MVP</label>
```

Change the route signature:

```python
    run_inline: str = Form(default="yes"),
```

Then use:

```python
    if run_inline == "yes":
        run_search_task(session, task.id)
    else:
        from app.jobs.queue import get_queue
        from app.jobs.worker import run_search_task_job
        get_queue().enqueue(run_search_task_job, task.id)
```

- [ ] **Step 5: Run tests**

Run:

```powershell
python -m pytest tests/test_queue.py -q
python -m pytest -q
```

Expected: PASS for both commands.

- [ ] **Step 6: Commit**

Run:

```powershell
git add app/jobs app/web/routes.py app/templates/search.html tests/test_queue.py
git commit -m "feat: add background search queue"
```

## Task 13: Docker Compose Deployment

**Files:**
- Create: `docker-compose.yml`
- Create: `Dockerfile`
- Modify: `README.md`

- [ ] **Step 1: Create Dockerfile**

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir -e ".[dev]"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create Docker Compose**

Create `docker-compose.yml`:

```yaml
services:
  web:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    depends_on:
      - redis

  worker:
    build: .
    command: rq worker influencer-search --url redis://redis:6379/0
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

- [ ] **Step 3: Update README deployment commands**

Append to `README.md`:

```markdown
## Docker Compose

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:8000`.
```

- [ ] **Step 4: Verify Docker config parses**

Run:

```powershell
docker compose config
```

Expected: command exits 0 and prints `services:` with `web`, `worker`, and `redis`.

- [ ] **Step 5: Commit**

Run:

```powershell
git add Dockerfile docker-compose.yml README.md
git commit -m "chore: add docker compose deployment"
```

## Task 14: End-To-End Verification

**Files:**
- Modify: `README.md`
- Create: `tests/test_acceptance.py`

- [ ] **Step 1: Write acceptance test**

Create `tests/test_acceptance.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_acceptance_search_to_results_to_export():
    client = TestClient(app)
    create_response = client.post(
        "/search",
        data={"input_text": "skincare", "platforms": ["youtube"], "run_inline": "yes"},
        follow_redirects=False,
    )
    assert create_response.status_code in {302, 303}
    task_url = create_response.headers["location"]

    detail_response = client.get(task_url)
    assert detail_response.status_code == 200
    assert "Search task" in detail_response.text
    assert "Ranked mainly by recent views" in detail_response.text

    export_response = client.get(f"{task_url}/export.xlsx")
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
```

- [ ] **Step 2: Run acceptance test**

Run:

```powershell
python -m pytest tests/test_acceptance.py -q
```

Expected: PASS.

- [ ] **Step 3: Run full verification**

Run:

```powershell
python -m pytest -q
python -m ruff check .
```

Expected: both commands exit 0.

- [ ] **Step 4: Start local app for manual verification**

Run:

```powershell
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`, search `skincare`, and verify:

- Search form loads.
- Search creates a task.
- Result table shows at least one creator.
- Excel export downloads.
- Due diligence card route opens for a result.

- [ ] **Step 5: Commit**

Run:

```powershell
git add README.md tests/test_acceptance.py
git commit -m "test: add mvp acceptance coverage"
```

## Implementation Notes

- Start with inline search execution checked by default so the MVP works without Redis during local testing.
- Keep TikTok and Instagram conservative in MVP: discover/profile URLs, public contact links, and DM entry paths only.
- Do not automate private messages.
- Do not scrape private or login-only data.
- Add real YouTube API key only in `.env`; never commit it.
- If a source fails, mark the task as failed only when every source fails. Otherwise show partial results with source notes.

## Self-Review

- Spec coverage:
  - Internal web UI: Tasks 7, 9, and 14.
  - Data model: Task 2.
  - Search inputs: Task 3.
  - Scoring: Task 4.
  - Mixed data connectors: Tasks 5, 10, and 11.
  - Async queue: Task 12.
  - Excel export: Task 8.
  - Deep due diligence cards: Task 9.
  - Local/lightweight deployment: Task 13.
  - MVP acceptance criteria: Task 14.
- Empty-field scan: no unfinished markers or incomplete task descriptions remain.
- Type consistency:
  - `Platform`, `TaskStatus`, `SearchTask`, `Creator`, `PlatformAccount`, `ContactRecord`, `ContentSample`, and `ScoreResult` are defined in Task 2 and reused consistently.
  - `RawCandidate`, `RawContent`, and `RawContact` are defined in Task 5 and reused by connector tasks.
  - `CandidateMetrics` and `ScoredCandidate` are defined in Task 4 and reused by the search runner.
