"""Phase 1 health endpoint tests."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["app_name"] == "ShopSphere AI Returns Agent"
    assert body["app_env"] == "development"
    assert body["version"] == "0.1.0"
    assert body["status"] in ("ok", "not_ready", "degraded")
    names = {dep["name"] for dep in body["dependencies"]}
    assert names == {"sqlite", "chroma", "llm"}


def test_openapi_available() -> None:
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    assert "paths" in response.json()
