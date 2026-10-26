"""Phase 7 chat API and tool tests."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agents.context import clear_agent_context, set_agent_context
from app.main import app
from app.models.enums import UserRole
from app.models.tables import User
from app.security.deps import CurrentUser
from app.security.passwords import hash_password
from app.tools.sql_tools import get_return_details

client = TestClient(app)


def _login(populated_db, username: str, role: UserRole) -> str:
    populated_db.add(
        User(
            username=username,
            password_hash=hash_password("chat-test-pass"),
            role=role.value,
            active=True,
        )
    )
    populated_db.commit()
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "chat-test-pass"},
    )
    return response.json()["access_token"]


def test_sql_tool_get_return_r102(populated_db) -> None:
    set_agent_context(
        populated_db,
        CurrentUser(user_id=1, username="tool_tester", role=UserRole.ADMINISTRATOR),
    )
    try:
        payload = get_return_details.invoke({"return_id": "R102"})
    finally:
        clear_agent_context()
    assert "R102" in payload
    assert "return_status" in payload


def test_chat_requires_llm_config(populated_db, monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    from app.config import get_settings
    from app.agents.graph import clear_agent_graph_cache

    get_settings.cache_clear()
    clear_agent_graph_cache()

    token = _login(populated_db, "chat_user1", UserRole.RETURNS_ANALYST)
    response = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "What is the status of R102?"},
    )
    assert response.status_code == 503


@patch("app.routes.chat.run_agent_chat")
def test_chat_success_with_mock_agent(mock_run, populated_db, monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    from app.config import get_settings
    from app.agents.graph import clear_agent_graph_cache

    get_settings.cache_clear()
    clear_agent_graph_cache()

    mock_run.return_value = {
        "final_response": "Return R102 is under investigation due to a serial mismatch.",
        "tool_events": [{"tool": "get_return_details", "args": {"return_id": "R102"}}],
        "inferred_return_id": "R102",
        "message_count": 3,
    }

    token = _login(populated_db, "chat_user2", UserRole.RETURNS_ANALYST)
    response = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Investigate R102", "return_id": "R102"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "serial mismatch" in body["final_response"].lower()
    assert body["llm_provider"] == "groq"
    assert body["tool_events"]


def test_llm_providers_endpoint(populated_db, monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("GEMINI_API_KEY", "gem")
    from app.config import get_settings

    get_settings.cache_clear()

    token = _login(populated_db, "llm_list_user", UserRole.RETURNS_ANALYST)
    response = client.get(
        "/api/llm/providers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["default_provider"] in {"groq", "gemini"}
    ids = {p["id"] for p in body["providers"]}
    assert ids == {"groq", "gemini"}
