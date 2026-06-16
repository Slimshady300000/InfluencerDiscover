from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_compose_publishes_web_only_on_loopback_and_keeps_redis_internal():
    compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert '"127.0.0.1:8000:8000"' in compose_text
    assert '"8000:8000"' not in compose_text
    assert '"6379:6379"' not in compose_text


def test_dockerfile_uses_render_port_environment_variable():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "${PORT:-8000}" in dockerfile
    assert "uvicorn app.main:app" in dockerfile


def test_runtime_dependencies_include_postgres_driver():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "psycopg2-binary" in pyproject


def test_render_deployment_files_exist():
    assert (ROOT / "render.yaml").is_file()
    assert (ROOT / "docs" / "render-neon-deploy.md").is_file()


def test_render_blueprint_uses_free_docker_web_service_with_manual_secrets():
    blueprint = yaml.safe_load((ROOT / "render.yaml").read_text(encoding="utf-8"))

    service = blueprint["services"][0]
    env_vars = {item["key"]: item for item in service["envVars"]}

    assert service["type"] == "web"
    assert service["runtime"] == "docker"
    assert service["plan"] == "free"
    assert service["autoDeployTrigger"] == "commit"
    assert "autoDeploy" not in service
    assert env_vars["DATABASE_URL"]["sync"] is False
    assert env_vars["ACCESS_PASSWORD"]["sync"] is False
