from base64 import b64encode

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
import app.main as main_module


class AuthSettings:
    def __init__(self, access_username: str = "", access_password: str = ""):
        self.access_username = access_username
        self.access_password = access_password


@pytest.fixture
def session_engine(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    return engine


def make_auth_header(username: str, password: str) -> str:
    token = b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


def make_client(session_engine, monkeypatch, username: str = "", password: str = ""):
    def override_session():
        with Session(session_engine) as session:
            yield session

    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(main_module, "settings", AuthSettings(username, password))
    previous_overrides = dict(main_module.app.dependency_overrides)
    main_module.app.dependency_overrides[get_session] = override_session
    test_client = TestClient(main_module.app, raise_server_exceptions=False)
    return test_client, previous_overrides


def test_access_is_open_when_credentials_are_not_configured(session_engine, monkeypatch):
    client, previous_overrides = make_client(session_engine, monkeypatch)
    with client:
        response = client.get("/")
    main_module.app.dependency_overrides = previous_overrides

    assert response.status_code == 200
    assert "Influencer Discovery" in response.text


def test_configured_basic_auth_blocks_missing_or_invalid_credentials(
    session_engine,
    monkeypatch,
):
    client, previous_overrides = make_client(session_engine, monkeypatch, "team", "secret")
    with client:
        missing_response = client.get("/")
        invalid_response = client.get(
            "/",
            headers={"Authorization": make_auth_header("team", "wrong")},
        )
    main_module.app.dependency_overrides = previous_overrides

    assert missing_response.status_code == 401
    assert missing_response.headers["www-authenticate"] == 'Basic realm="Influencer Discovery"'
    assert invalid_response.status_code == 401


def test_configured_basic_auth_allows_valid_credentials(session_engine, monkeypatch):
    client, previous_overrides = make_client(session_engine, monkeypatch, "team", "secret")
    with client:
        response = client.get(
            "/",
            headers={"Authorization": make_auth_header("team", "secret")},
        )
    main_module.app.dependency_overrides = previous_overrides

    assert response.status_code == 200
    assert "Influencer Discovery" in response.text
