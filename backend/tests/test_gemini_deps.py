"""Gemini chat model builds without langchain-google-genai (uses OpenAI-compatible API)."""

from unittest.mock import patch

from app.llm.gemini import GEMINI_OPENAI_BASE_URL, get_gemini_chat_model
from app.llm.guarded import GuardedChatModel


def test_get_gemini_chat_model_uses_openai_compat(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    from app.config import get_settings

    get_settings.cache_clear()

    with patch("app.llm.gemini.GeminiChatOpenAI") as mock_chat:
        mock_chat.return_value = object()
        model = get_gemini_chat_model()

    assert isinstance(model, GuardedChatModel)
    mock_chat.assert_called_once()
    kwargs = mock_chat.call_args.kwargs
    assert kwargs["base_url"] == GEMINI_OPENAI_BASE_URL
    assert kwargs["api_key"] == "test-key"
    assert kwargs["model"] == "gemini-3.5-flash-lite"
    assert kwargs.get("disable_streaming") is True


def test_gemini_stream_agent_round_trip(monkeypatch) -> None:
    """Streaming chat must not use LLM streaming for tool calls (thought_signature)."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    from app.agents.graph import clear_agent_graph_cache

    clear_agent_graph_cache()
    from app.llm.gemini import get_gemini_chat_model

    model = get_gemini_chat_model()
    assert model.inner.disable_streaming is True
