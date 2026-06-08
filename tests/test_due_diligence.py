import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
import app.main as main_module
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
from app.services.due_diligence import build_due_diligence_card


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


def test_build_due_diligence_card_uses_fallbacks_for_blank_titles_no_contact_or_risks():
    card = build_due_diligence_card(
        creator_name="Creator B",
        platform="TikTok",
        follower_count=120000,
        score=72.5,
        content_titles=["", "   ", "\t"],
        contact="",
        risks=[],
    )

    assert card.representative_content == "No recent content samples stored."
    assert card.risks == "No obvious risk found in stored data."
    assert card.suggested_contact == "Use public DM entry if visible on the profile."


def test_result_card_renders_persisted_due_diligence_data(client, db_session):
    creator = Creator(display_name="Creator A", primary_topics="skincare")
    account = PlatformAccount(
        creator=creator,
        platform=Platform.youtube,
        handle="@creator",
        profile_url="https://example.com/creator",
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
            source_url="https://example.com/creator",
        )
    )
    db_session.add(
        ContentSample(
            account_id=account.id,
            content_url="https://example.com/video-1",
            title="Hydrating serum review",
            view_count=1000,
        )
    )
    result = ScoreResult(
        task_id=task.id,
        creator_id=creator.id,
        platform_account_id=account.id,
        final_score=87.0,
        risks="No recent sponsored content found.",
    )
    db_session.add(result)
    db_session.commit()

    response = client.get(f"/results/{result.id}/card")

    assert response.status_code == 200
    assert "Creator A" in response.text
    assert "Hydrating serum review" in response.text
    assert "No recent sponsored content found." in response.text
    assert "business@example.com" in response.text
