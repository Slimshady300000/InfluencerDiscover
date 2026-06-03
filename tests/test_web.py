from fastapi.testclient import TestClient

from app.main import app


def test_homepage_returns_search_screen():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Influencer Discovery" in response.text
