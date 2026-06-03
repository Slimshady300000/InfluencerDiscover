from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app


def test_homepage_returns_search_screen():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Influencer Discovery" in response.text


def test_settings_ignore_extra_env_file_values(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath(".env").write_text(
        "APP_NAME=Influencer Discovery\nUNRELATED_SETTING=value\n",
        encoding="utf-8",
    )

    settings = Settings()

    assert settings.app_name == "Influencer Discovery"
