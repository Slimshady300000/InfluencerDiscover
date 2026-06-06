from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app


def test_homepage_returns_search_screen():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "Influencer Discovery" in response.text
    assert "Start Search" in response.text


def test_create_search_task_redirects_to_task_page():
    with TestClient(app) as client:
        response = client.post(
            "/search",
            data={"input_text": "skincare", "platforms": ["youtube"]},
            follow_redirects=False,
        )
    assert response.status_code in {302, 303}
    assert "/tasks/" in response.headers["location"]


def test_settings_ignore_extra_env_file_values(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath(".env").write_text(
        "APP_NAME=Influencer Discovery\nUNRELATED_SETTING=value\n",
        encoding="utf-8",
    )

    settings = Settings()

    assert settings.app_name == "Influencer Discovery"
