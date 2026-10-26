"""Agent capability discovery API."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_agent_capabilities_public() -> None:
    response = client.get("/api/agent/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) >= 5
    assert body[0]["id"] == "investigate"
    assert "run_return_investigation" in body[0]["tools"]
