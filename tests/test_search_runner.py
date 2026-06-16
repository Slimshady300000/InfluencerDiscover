import json

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from app.connectors.base import RawCandidate, RawContent
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
import app.services.search_runner as search_runner
from app.services.search_runner import run_search_task


class SearchSettings:
    youtube_api_key = ""
    tavily_api_key = ""
    search_engine_api_key = "search-key"
    search_engine_id = "cx"


class NoLiveSettings:
    youtube_api_key = ""
    tavily_api_key = ""
    search_engine_api_key = ""
    search_engine_id = ""


class TavilySettings:
    youtube_api_key = ""
    tavily_api_key = "tvly-test"
    search_engine_api_key = ""
    search_engine_id = ""


class EmptyCrawlerConnector:
    def __init__(self):
        self.last_status = {}

    def search(self, intent):
        self.last_status = {
            platform.value: {
                "query": f"site:{platform.value}.com skincare creator contact",
                "returned_count": 0,
                "parsed_count": 0,
                "fetched_count": 0,
                "skipped_count": 0,
                "errors": [],
            }
            for platform in intent.platforms
        }
        return []


def test_manual_connector_returns_candidates():
    intent = parse_search_input("skincare", [Platform.youtube])
    connector = ManualConnector()
    candidates = connector.search(intent)
    assert candidates
    assert candidates[0].platform == Platform.youtube
    assert candidates[0].handle.startswith("@")


def test_manual_connector_returns_candidate_for_each_selected_platform():
    intent = parse_search_input("skincare", [Platform.youtube, Platform.tiktok, Platform.instagram])
    connector = ManualConnector()

    candidates = connector.search(intent)

    assert {candidate.platform for candidate in candidates} == {
        Platform.youtube,
        Platform.tiktok,
        Platform.instagram,
    }
    assert len({candidate.profile_url for candidate in candidates}) == len(candidates)


def test_manual_connector_returns_reviewable_volume_for_each_selected_platform():
    intent = parse_search_input("skincare", [Platform.youtube, Platform.tiktok, Platform.instagram])
    connector = ManualConnector()

    candidates = connector.search(intent)

    assert len(candidates) >= 24
    for platform in [Platform.youtube, Platform.tiktok, Platform.instagram]:
        platform_candidates = [
            candidate for candidate in candidates if candidate.platform == platform
        ]
        assert len(platform_candidates) >= 8
        assert len({candidate.profile_url for candidate in platform_candidates}) >= 8


def test_run_search_task_persists_candidates_and_scores(monkeypatch):
    monkeypatch.setattr(search_runner, "get_settings", lambda: NoLiveSettings())
    monkeypatch.setattr(search_runner, "WebCrawlerConnector", EmptyCrawlerConnector)

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        task = SearchTask(
            input_text="skincare",
            input_type="keyword",
            platforms="youtube",
            status=TaskStatus.queued,
            use_demo_data=True,
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        run_search_task(session, task.id)

        saved_task = session.get(SearchTask, task.id)
        creators = session.exec(select(Creator)).all()
        assert saved_task.status == TaskStatus.complete
        assert len(creators) == 8
        assert saved_task.results[0].final_score > 0

        contents = session.exec(select(ContentSample)).all()
        contacts = session.exec(select(ContactRecord)).all()
        assert len(contents) == 8
        assert contents[0].title == "Hydrating serum review"
        assert len(contacts) == 8
        assert contacts[0].value == "business@example.com"


def test_run_search_task_persists_candidates_for_each_selected_platform(monkeypatch):
    monkeypatch.setattr(search_runner, "get_settings", lambda: NoLiveSettings())
    monkeypatch.setattr(search_runner, "WebCrawlerConnector", EmptyCrawlerConnector)

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        task = SearchTask(
            input_text="skincare",
            input_type="keyword",
            platforms="youtube,tiktok,instagram",
            status=TaskStatus.queued,
            use_demo_data=True,
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        run_search_task(session, task.id)

        accounts = session.exec(select(PlatformAccount)).all()
        results = session.exec(select(ScoreResult)).all()
        assert {account.platform for account in accounts} == {
            Platform.youtube,
            Platform.tiktok,
            Platform.instagram,
        }
        assert len(results) >= 24


def test_run_search_task_uses_search_engine_connector_when_configured(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    class FakeSearchEngineConnector:
        def __init__(self, api_key, search_engine_id):
            assert api_key == "search-key"
            assert search_engine_id == "cx"

        def search(self, _intent):
            return [
                RawCandidate(
                    platform=Platform.youtube,
                    handle="@live_creator",
                    display_name="Live Creator",
                    profile_url="https://www.youtube.com/@live_creator",
                    follower_count=0,
                    bio="Live search result",
                    contents=[
                        RawContent(
                            content_url="https://www.youtube.com/@live_creator",
                            title="Live Creator - YouTube",
                            description="Live search result",
                        )
                    ],
                )
            ]

    monkeypatch.setattr(search_runner, "get_settings", lambda: SearchSettings())
    monkeypatch.setattr(search_runner, "WebCrawlerConnector", EmptyCrawlerConnector)
    monkeypatch.setattr(search_runner, "SearchEngineConnector", FakeSearchEngineConnector)

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

        creators = session.exec(select(Creator)).all()
        assert [creator.display_name for creator in creators] == ["Live Creator"]


def test_run_search_task_uses_tavily_connector_before_crawler_when_configured(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    class FakeTavilyConnector:
        def __init__(self, api_key):
            assert api_key == "tvly-test"
            self.last_status = {
                "youtube": {
                    "query": "skincare creator contact",
                    "returned_count": 1,
                    "parsed_count": 1,
                    "fetched_count": 0,
                    "skipped_count": 0,
                    "errors": [],
                }
            }

        def search(self, _intent):
            return [
                RawCandidate(
                    platform=Platform.youtube,
                    handle="@tavily_creator",
                    display_name="Tavily Creator",
                    profile_url="https://www.youtube.com/@tavily_creator",
                    follower_count=0,
                    bio="Tavily search result",
                    contents=[
                        RawContent(
                            content_url="https://www.youtube.com/@tavily_creator",
                            title="Tavily Creator - YouTube",
                            description="Tavily search result",
                        )
                    ],
                )
            ]

    class FailingCrawlerConnector:
        def search(self, _intent):
            raise AssertionError("crawler should not run before configured Tavily search")

    monkeypatch.setattr(search_runner, "get_settings", lambda: TavilySettings())
    monkeypatch.setattr(search_runner, "TavilyConnector", FakeTavilyConnector)
    monkeypatch.setattr(search_runner, "WebCrawlerConnector", FailingCrawlerConnector)

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

        creators = session.exec(select(Creator)).all()
        saved_task = session.get(SearchTask, task.id)
        connector_status = json.loads(saved_task.connector_status)
        assert [creator.display_name for creator in creators] == ["Tavily Creator"]
        assert connector_status["mode"] == "real_tavily_search"
        assert connector_status["platforms"]["youtube"]["parsed_count"] == 1


def test_collect_raw_candidates_does_not_use_demo_by_default(monkeypatch):
    class FailingManualConnector:
        def search(self, _intent):
            raise AssertionError("demo fallback should not run by default")

    monkeypatch.setattr(search_runner, "get_settings", lambda: NoLiveSettings())
    monkeypatch.setattr(search_runner, "WebCrawlerConnector", EmptyCrawlerConnector)
    monkeypatch.setattr(search_runner, "ManualConnector", FailingManualConnector)
    intent = parse_search_input("skincare", [Platform.youtube])

    collection = search_runner.collect_candidates_with_status(intent, use_demo_data=False)

    assert collection.candidates == []
    assert collection.connector_status["demo_used"] is False
    assert collection.connector_status["real_result_count"] == 0
    assert "No real public results" in collection.connector_status["summary"]


def test_collect_raw_candidates_uses_demo_only_when_requested(monkeypatch):
    monkeypatch.setattr(search_runner, "get_settings", lambda: NoLiveSettings())
    monkeypatch.setattr(search_runner, "WebCrawlerConnector", EmptyCrawlerConnector)
    intent = parse_search_input("skincare", [Platform.youtube])

    collection = search_runner.collect_candidates_with_status(intent, use_demo_data=True)

    assert len(collection.candidates) == 8
    assert {candidate.data_source for candidate in collection.candidates} == {"demo_fallback"}
    assert collection.connector_status["demo_used"] is True
    assert collection.connector_status["demo_result_count"] == 8


def test_run_search_task_records_no_real_results_without_demo(monkeypatch):
    monkeypatch.setattr(search_runner, "get_settings", lambda: NoLiveSettings())
    monkeypatch.setattr(search_runner, "WebCrawlerConnector", EmptyCrawlerConnector)

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
        connector_status = json.loads(saved_task.connector_status)
        assert saved_task.status == TaskStatus.complete
        assert saved_task.error_summary == "No real public results found."
        assert connector_status["real_result_count"] == 0
        assert connector_status["demo_used"] is False
        assert session.exec(select(Creator)).all() == []


def test_run_search_task_rolls_back_candidate_rows_when_scoring_fails(monkeypatch):
    monkeypatch.setattr(search_runner, "get_settings", lambda: NoLiveSettings())
    monkeypatch.setattr(search_runner, "WebCrawlerConnector", EmptyCrawlerConnector)

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        task = SearchTask(
            input_text="skincare",
            input_type="keyword",
            platforms="youtube",
            status=TaskStatus.queued,
            use_demo_data=True,
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        def fail_scoring(_metrics):
            raise RuntimeError("scoring failed")

        monkeypatch.setattr(search_runner, "score_batch", fail_scoring)

        with pytest.raises(RuntimeError, match="scoring failed"):
            run_search_task(session, task.id)

        saved_task = session.get(SearchTask, task.id)
        assert saved_task.status == TaskStatus.failed
        assert saved_task.error_summary == "scoring failed"
        assert session.exec(select(Creator)).all() == []
        assert session.exec(select(PlatformAccount)).all() == []
        assert session.exec(select(ContentSample)).all() == []
        assert session.exec(select(ContactRecord)).all() == []
        assert session.exec(select(ScoreResult)).all() == []


def test_run_search_task_rolls_back_before_marking_failed(monkeypatch):
    monkeypatch.setattr(search_runner, "get_settings", lambda: NoLiveSettings())
    monkeypatch.setattr(search_runner, "WebCrawlerConnector", EmptyCrawlerConnector)

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        task = SearchTask(
            input_text="skincare",
            input_type="keyword",
            platforms="youtube",
            status=TaskStatus.queued,
            use_demo_data=True,
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        class BrokenConnector:
            def search(self, _intent):
                return [
                    RawCandidate(
                        platform=Platform.youtube,
                        handle="@broken",
                        display_name="Broken Creator",
                        profile_url="https://example.com/youtube/broken",
                        follower_count=1,
                        contents=[
                            RawContent(
                                content_url=None,
                                title="Invalid content row",
                            )
                        ],
                    )
                ]

        monkeypatch.setattr(search_runner, "ManualConnector", BrokenConnector)

        with pytest.raises(IntegrityError):
            run_search_task(session, task.id)

        saved_task = session.get(SearchTask, task.id)
        assert saved_task.status == TaskStatus.failed
        assert "contentsample.content_url" in saved_task.error_summary
        assert session.exec(select(Creator)).all() == []
