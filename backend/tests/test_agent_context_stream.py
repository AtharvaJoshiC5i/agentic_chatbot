"""Agent DB context must be available during streamed LangGraph tool calls."""

from langchain_core.runnables.config import var_child_runnable_config

from app.agents.context import agent_run_config, clear_agent_context, get_agent_db, get_agent_user
from app.models.tables import Return
from app.agents.graph import stream_agent_chat
from app.models.enums import UserRole
from app.security.deps import CurrentUser


def test_get_agent_db_opens_session_when_user_in_config(populated_db) -> None:
    user = CurrentUser(user_id=1, username="ctx", role=UserRole.ADMINISTRATOR)
    clear_agent_context()
    run_config = agent_run_config(None, user)
    assert run_config is not None
    token = var_child_runnable_config.set(run_config)
    try:
        session = get_agent_db()
        assert session is not populated_db
        assert get_agent_user() is user
        assert session.get(Return, "R101") is not None
    finally:
        clear_agent_context()
        var_child_runnable_config.reset(token)


def test_stream_agent_chat_passes_user_via_langgraph_config(populated_db, monkeypatch) -> None:
    user = CurrentUser(user_id=1, username="stream_ctx", role=UserRole.ADMINISTRATOR)
    clear_agent_context()
    seen_config: dict = {}

    class FakeGraph:
        def stream(self, _input, stream_mode="values", config=None):
            seen_config["value"] = config
            state = {"messages": _input["messages"]}
            modes = stream_mode if isinstance(stream_mode, (list, tuple)) else [stream_mode]
            for mode in modes:
                if mode == "values":
                    yield ("values", state)

    monkeypatch.setattr(
        "app.agents.graph.get_agent_graph",
        lambda _provider, _role_key: FakeGraph(),
    )

    events = list(
        stream_agent_chat(
            "Status of R102?",
            llm_provider="groq",
            db=populated_db,
            user=user,
        )
    )
    assert any(e.get("event") == "done" for e in events)
    cfg = seen_config.get("value")
    assert cfg is not None
    assert cfg["configurable"]["agent_user"] is user
    assert "agent_db" not in cfg["configurable"]
    clear_agent_context()
