from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
import app.main as main_module


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


def test_acceptance_search_to_results_to_export_and_card(client):
    create_response = client.post(
        "/search",
        data={
            "input_text": "skincare",
            "platforms": ["youtube", "tiktok", "instagram"],
            "run_inline": "yes",
        },
        follow_redirects=False,
    )
    assert create_response.status_code in {302, 303}
    task_url = create_response.headers["location"]

    detail_response = client.get(task_url)
    assert detail_response.status_code == 200
    assert "Search task" in detail_response.text
    assert "Ranked mainly by recent views" in detail_response.text
    assert "Creator A" in detail_response.text
    assert "Creator B" in detail_response.text
    assert "Creator C" in detail_response.text
    assert "/export.xlsx" in detail_response.text
    assert "/results/" in detail_response.text
    assert "/card" in detail_response.text

    export_response = client.get(f"{task_url}/export.xlsx")
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    workbook = load_workbook(BytesIO(export_response.content))
    sheet = workbook.active
    assert sheet["A1"].value == "Creator"
    assert {sheet["A2"].value, sheet["A3"].value, sheet["A4"].value} == {
        "Creator A",
        "Creator B",
        "Creator C",
    }
    assert {sheet["B2"].value, sheet["B3"].value, sheet["B4"].value} == {
        "youtube",
        "tiktok",
        "instagram",
    }

    card_path = _extract_first_card_path(detail_response.text)
    card_response = client.get(card_path)
    assert card_response.status_code == 200
    assert any(name in card_response.text for name in {"Creator A", "Creator B", "Creator C"})
    assert "Recommendation:" in card_response.text


def _extract_first_card_path(html: str) -> str:
    marker = 'href="/results/'
    start = html.index(marker) + len('href="')
    end = html.index('"', start)
    return html[start:end]
