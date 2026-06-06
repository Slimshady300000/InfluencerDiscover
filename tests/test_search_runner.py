from app.connectors.manual import ManualConnector
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Creator, Platform, SearchTask, TaskStatus
from app.services.query_parser import parse_search_input
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
