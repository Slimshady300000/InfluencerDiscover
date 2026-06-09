from pathlib import Path


def test_compose_publishes_web_only_on_loopback_and_keeps_redis_internal():
    compose_text = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert '"127.0.0.1:8000:8000"' in compose_text
    assert '"8000:8000"' not in compose_text
    assert '"6379:6379"' not in compose_text
