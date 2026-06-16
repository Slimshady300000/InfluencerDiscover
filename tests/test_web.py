import json

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
    assert "达人发现" in response.text
    assert "开始搜索" in response.text
    assert "真实公开搜索" in response.text


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
    assert 'class="workbench-shell"' in response.text
    assert 'class="side-nav"' in response.text
    assert 'class="platform-card"' in response.text
    assert 'class="primary-button"' in response.text
    assert 'class="status-badge status-complete"' in response.text
    assert 'name="platforms" value="youtube" checked' in response.text
    assert 'name="platforms" value="tiktok" checked' in response.text
    assert 'name="platforms" value="instagram" checked' in response.text
    assert 'name="use_demo_data" value="yes" checked' not in response.text


def test_create_search_task_redirects_to_task_page(client, monkeypatch):
    monkeypatch.setattr(routes, "run_search_task", lambda _session, _task_id: None)
    response = client.post(
        "/search",
        data={"input_text": "skincare", "platforms": ["youtube"]},
        follow_redirects=False,
    )
    assert response.status_code in {302, 303}
    assert "/tasks/" in response.headers["location"]


def test_create_search_task_stores_demo_fallback_switch(client, db_session, monkeypatch):
    monkeypatch.setattr(routes, "run_search_task", lambda _session, _task_id: None)

    response = client.post(
        "/search",
        data={
            "input_text": "skincare",
            "platforms": ["youtube", "tiktok", "instagram"],
            "use_demo_data": "yes",
        },
        follow_redirects=False,
    )

    assert response.status_code in {302, 303}
    task = db_session.exec(select(SearchTask)).one()
    assert task.platforms == "youtube,tiktok,instagram"
    assert task.use_demo_data is True


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
        data_source="real_public",
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
            reasons="Strong topic fit | Public contact found | Recent content present",
        )
    )
    db_session.commit()

    response = client.get(f"/tasks/{task.id}")

    assert response.status_code == 200
    assert 'class="creator-card"' in response.text
    assert "compact-review-table" in response.text
    assert "达人" in response.text
    assert "平台" in response.text
    assert "主页" in response.text
    assert "粉丝数" in response.text
    assert "平均播放" in response.text
    assert "互动率" in response.text
    assert "联系方式" in response.text
    assert "Reasons" not in response.text
    assert "真实公开结果" in response.text
    assert "话题匹配度高" in response.text
    assert "Creator A" in response.text
    assert "youtube" in response.text
    assert "https://www.youtube.com/@creator_a" in response.text
    assert "310000" in response.text
    assert "1000" in response.text
    assert "11.00%" in response.text
    assert "business@example.com" in response.text


def test_task_detail_shows_unknown_for_missing_real_follower_count(client, db_session):
    creator = Creator(display_name="Creator Zero", primary_topics="skincare")
    account = PlatformAccount(
        creator=creator,
        platform=Platform.tiktok,
        handle="@creator_zero",
        profile_url="https://www.tiktok.com/@creator_zero",
        follower_count=0,
        data_source="real_public",
    )
    task = SearchTask(
        input_text="skincare",
        input_type="keyword",
        platforms="tiktok",
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
            final_score=0.72,
        )
    )
    db_session.commit()

    response = client.get(f"/tasks/{task.id}")

    assert response.status_code == 200
    assert "粉丝数：未获取" in response.text
    assert "<td class=\"metric\">未获取</td>" in response.text


def test_task_detail_shows_empty_real_result_state(client, db_session):
    task = SearchTask(
        input_text="rings",
        input_type="keyword",
        platforms="youtube,tiktok,instagram",
        status=TaskStatus.complete,
        error_summary="未找到真实公开结果。",
        connector_status=json.dumps(
            {
                "mode": "real_crawler",
                "searched_platforms": ["youtube", "tiktok", "instagram"],
                "real_result_count": 0,
                "demo_used": False,
                "demo_result_count": 0,
                "summary": "未找到真实公开结果。",
                "platforms": {
                    "youtube": {
                        "query": "site:youtube.com rings creator contact",
                        "returned_count": 0,
                        "parsed_count": 0,
                        "fetched_count": 0,
                        "skipped_count": 0,
                        "errors": ["search source returned no usable links"],
                    }
                },
            }
        ),
    )
    db_session.add(task)
    db_session.commit()

    response = client.get(f"/tasks/{task.id}")

    assert response.status_code == 200
    assert "未找到真实公开结果。" in response.text
    assert "启用演示数据" in response.text
    assert "site:youtube.com rings creator contact" in response.text


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
