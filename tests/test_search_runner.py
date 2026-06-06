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


def test_manual_connector_returns_candidates():
    intent = parse_search_input("skincare", [Platform.youtube])
    connector = ManualConnector()
    candidates = connector.search(intent)
    assert candidates
    assert candidates[0].platform == Platform.youtube
    assert candidates[0].handle.startswith("@")


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

        contents = session.exec(select(ContentSample)).all()
        contacts = session.exec(select(ContactRecord)).all()
        assert len(contents) == 1
        assert contents[0].title == "Hydrating serum review"
        assert len(contacts) == 1
        assert contacts[0].value == "business@example.com"


def test_run_search_task_rolls_back_candidate_rows_when_scoring_fails(monkeypatch):
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
