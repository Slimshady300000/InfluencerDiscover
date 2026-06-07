from io import BytesIO

from openpyxl import load_workbook

from app.services.exporter import build_candidate_workbook


def test_build_candidate_workbook_contains_expected_headers():
    data = [
        {
            "creator": "Creator A",
            "platform": "YouTube",
            "followers": 310000,
            "recent_views": 96000,
            "engagement_rate": 0.071,
            "score": 87.0,
            "contact": "business@example.com",
        }
    ]
    payload = build_candidate_workbook(data)
    workbook = load_workbook(BytesIO(payload))
    sheet = workbook.active
    assert sheet["A1"].value == "Creator"
    assert sheet["G2"].value == "business@example.com"
