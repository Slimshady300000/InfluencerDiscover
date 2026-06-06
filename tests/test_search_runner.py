from app.connectors.manual import ManualConnector
from app.models import Platform
from app.services.query_parser import parse_search_input


def test_manual_connector_returns_candidates():
    intent = parse_search_input("skincare", [Platform.youtube])
    connector = ManualConnector()
    candidates = connector.search(intent)
    assert candidates
    assert candidates[0].platform == Platform.youtube
    assert candidates[0].handle.startswith("@")
