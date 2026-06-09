import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select

from app.config import Settings
from app.db import get_session
import app.main as main_module
from app.models import (
    ContactRecord,
    ContentSample,
    Creator,
    FollowUp,
    Platform,
    PlatformAccount,
    ScoreResult,
    SearchTask,
    TaskStatus,
)
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


def test_homepage_returns_search_screen(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Influencer Discovery" in response.text
    assert "Start Search" in response.text


def test_homepage_uses_polished_search_ui(client, db_session):
    db_session.add(
        SearchTask(
            input_text="skincare",
            input_type="keyword",
            platforms="youtube,tiktok,instagram",
            status=TaskStatus.complete,
        )
    )
    db_session.commit()

    response = client.get("/")

    assert response.status_code == 200
    assert 'class="hero-panel"' in response.text
    assert 'class="platform-option"' in response.text
    assert 'class="primary-button"' in response.text
    assert 'class="status-badge status-complete"' in response.text


def test_create_search_task_redirects_to_task_page(client, monkeypatch):
    monkeypatch.setattr(routes, "run_search_task", lambda _session, _task_id: None)
    response = client.post(
        "/search",
        data={"input_text": "skincare", "platforms": ["youtube"]},
        follow_redirects=False,
    )
    assert response.status_code in {302, 303}
    assert "/tasks/" in response.headers["location"]


def test_task_detail_returns_404_for_missing_task(client):
    response = client.get("/tasks/999")

    assert response.status_code == 404


def test_task_detail_shows_manager_candidate_fields(client, db_session):
    creator = Creator(display_name="Creator A", primary_topics="skincare")
    account = PlatformAccount(
        creator=creator,
        platform=Platform.youtube,
        handle="@creator_a",
        profile_url="https://www.youtube.com/@creator_a",
        follower_count=310000,
    )
    task = SearchTask(
        input_text="skincare",
        input_type="keyword",
        platforms="youtube",
        status=TaskStatus.complete,
    )
    db_session.add(account)
    db_session.add(task)
    db_session.flush()
    db_session.add(
        ContactRecord(
            creator_id=creator.id,
            contact_type="email",
            value="business@example.com",
            source_url="https://www.youtube.com/@creator_a",
        )
    )
    db_session.add(
        ContentSample(
            account_id=account.id,
            content_url="https://www.youtube.com/watch?v=1",
            view_count=1000,
            like_count=80,
            comment_count=20,
            share_count=10,
        )
    )
    db_session.add(
        ScoreResult(
            task_id=task.id,
            creator_id=creator.id,
            platform_account_id=account.id,
            final_score=0.91,
        )
    )
    db_session.commit()

    response = client.get(f"/tasks/{task.id}")

    assert response.status_code == 200
    assert "Creator" in response.text
    assert "Platform" in response.text
    assert "Profile" in response.text
    assert "Followers" in response.text
    assert "Avg Views" in response.text
    assert "Engagement Rate" in response.text
    assert "Contact" in response.text
    assert "Creator A" in response.text
    assert "youtube" in response.text
    assert "https://www.youtube.com/@creator_a" in response.text
    assert "310000" in response.text
    assert "1000" in response.text
    assert "11.00%" in response.text
    assert "business@example.com" in response.text


def test_create_search_task_redirects_when_runner_marks_failed(
    client,
    monkeypatch,
):
    def fail_search_task(session: Session, task_id: int) -> None:
        task = session.get(SearchTask, task_id)
        task.status = TaskStatus.failed
        task.error_summary = "connector unavailable"
        session.add(task)
        session.commit()
        raise RuntimeError("connector unavailable")

    monkeypatch.setattr(routes, "run_search_task", fail_search_task)

    response = client.post(
        "/search",
        data={"input_text": "skincare", "platforms": ["youtube"]},
        follow_redirects=False,
    )

    assert response.status_code in {302, 303}
    assert "/tasks/" in response.headers["location"]


def test_update_follow_up_state_creates_row_and_redirects(client, db_session):
    creator = Creator(display_name="Creator One", primary_topics="skincare")
    account = PlatformAccount(
        creator=creator,
        platform=Platform.youtube,
        handle="@creator",
        profile_url="https://example.com/creator",
    )
    task = SearchTask(
        input_text="skincare",
        input_type="keyword",
        platforms="youtube",
        status=TaskStatus.complete,
    )
    db_session.add(account)
    db_session.add(task)
    db_session.flush()
    db_session.add(
        ScoreResult(
            task_id=task.id,
            creator_id=creator.id,
            platform_account_id=account.id,
            final_score=0.91,
        )
    )
    db_session.commit()

    response = client.post(
        f"/creators/{creator.id}/follow-up",
        data={
            "task_id": str(task.id),
            "owner": "Ava",
            "status": "Contacted",
            "tags": "priority,email",
            "notes": "Sent first outreach.",
        },
        follow_redirects=False,
    )

    assert response.status_code in {302, 303}
    assert response.headers["location"] == f"/tasks/{task.id}"
    follow_up = db_session.exec(select(FollowUp).where(FollowUp.creator_id == creator.id)).one()
    assert follow_up.owner == "Ava"
    assert follow_up.status == "Contacted"
    assert follow_up.tags == "priority,email"
    assert follow_up.notes == "Sent first outreach."
    detail_response = client.get(f"/tasks/{task.id}")
    assert "Ava" in detail_response.text
    assert "Contacted" in detail_response.text
    assert "priority,email" in detail_response.text
    assert "Sent first outreach." in detail_response.text


def test_settings_ignore_extra_env_file_values(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath(".env").write_text(
        "APP_NAME=Influencer Discovery\nUNRELATED_SETTING=value\n",
        encoding="utf-8",
    )

    settings = Settings()

    assert settings.app_name == "Influencer Discovery"
