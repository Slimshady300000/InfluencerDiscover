import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.jobs import worker
from app.jobs.queue import get_queue_name
import app.main as main_module
from app.models import SearchTask, TaskStatus
from app.web import routes


@pytest.fixture
def session_engine(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(session_engine, monkeypatch):
    def override_session():
        with Session(session_engine) as session:
            yield session

    monkeypatch.setattr(main_module, "init_db", lambda: None)
    previous_overrides = dict(main_module.app.dependency_overrides)
    main_module.app.dependency_overrides[get_session] = override_session
    with TestClient(main_module.app, raise_server_exceptions=False) as test_client:
        yield test_client
    main_module.app.dependency_overrides = previous_overrides


@pytest.fixture
def db_session(session_engine):
    with Session(session_engine) as session:
        yield session


def test_queue_name_is_stable():
    assert get_queue_name() == "influencer-search"


def test_worker_runs_search_task_with_session(session_engine, monkeypatch):
    called = {}

    def fake_run_search_task(session: Session, task_id: int) -> None:
        called["task_id"] = task_id
        called["session"] = session

    monkeypatch.setattr(worker, "engine", session_engine)
    monkeypatch.setattr(worker, "run_search_task", fake_run_search_task)

    worker.run_search_task_job(42)

    assert called["task_id"] == 42
    assert isinstance(called["session"], Session)


def test_create_search_task_can_enqueue_when_inline_disabled(client, db_session, monkeypatch):
    enqueued = {}

    class FakeQueue:
        def enqueue(self, job, task_id):
            enqueued["job"] = job
            enqueued["task_id"] = task_id

    def fail_inline(_session: Session, _task_id: int) -> None:
        raise AssertionError("inline search should not run when run_inline is no")

    monkeypatch.setattr(routes, "get_queue", lambda: FakeQueue())
    monkeypatch.setattr(routes, "run_search_task", fail_inline)

    response = client.post(
        "/search",
        data={"input_text": "skincare", "platforms": ["youtube"], "run_inline": ["no"]},
        follow_redirects=False,
    )

    assert response.status_code in {302, 303}
    task_id = int(response.headers["location"].removeprefix("/tasks/"))
    task = db_session.get(SearchTask, task_id)
    assert task.status == TaskStatus.queued
    assert enqueued == {"job": routes.run_search_task_job, "task_id": task_id}
