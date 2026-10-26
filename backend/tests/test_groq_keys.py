"""Multi-key Groq configuration and failover."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.llm.groq_rotating import GroqRotatingChatModel
from app.llm.rate_limit import reset_rate_limiters


def _clear_settings_cache() -> None:
    from app.config import get_settings

    get_settings.cache_clear()


def test_groq_api_keys_list_merges_primary_and_extra(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "key-a")
    monkeypatch.setenv("GROQ_API_KEYS", "key-b, key-c")
    _clear_settings_cache()
    from app.config import get_settings

    assert get_settings().groq_api_keys_list == ["key-a", "key-b", "key-c"]
    assert get_settings().groq_effective_max_rpm == 90


def test_groq_api_keys_only_in_groq_api_keys(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEYS", "only-one")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    _clear_settings_cache()
    from app.config import get_settings
    from app.llm.groq import is_groq_configured

    assert get_settings().groq_api_keys_list == ["only-one"]
    assert is_groq_configured() is True


def test_list_providers_reports_key_count(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "a")
    monkeypatch.setenv("GROQ_API_KEYS", "b")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("GROQ_MAX_RPM", "30")
    _clear_settings_cache()
    from app.llm.router import list_provider_options

    groq = next(p for p in list_provider_options() if p["id"] == "groq")
    assert groq["api_key_count"] == 2
    assert groq["max_rpm"] == 60
    assert groq["max_rpm_per_key"] == 30


def test_rotating_model_fails_over_on_429(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEYS", "k2")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    _clear_settings_cache()
    reset_rate_limiters()
    monkeypatch.setattr("app.llm.retry.time.sleep", lambda _: None)

    model = GroqRotatingChatModel(model="llama-3.3-70b-versatile", max_rpm_per_key=1000)
    calls: list[str] = []

    def fake_chat_for_key(api_key: str) -> MagicMock:
        calls.append(api_key)
        chat = MagicMock()
        if api_key == "k1":
            chat._generate.side_effect = RuntimeError("HTTP 429 Too Many Requests")
            chat.invoke.side_effect = RuntimeError("HTTP 429 Too Many Requests")
        else:
            chat._generate.return_value = MagicMock(
                generations=[MagicMock(message=AIMessage(content="ok"))]
            )
            chat.invoke.return_value = AIMessage(content="ok")
        return chat

    with patch.object(model, "_chat_for_key", side_effect=fake_chat_for_key):
        result = model._generate([HumanMessage(content="hi")])

    assert "k2" in calls
    assert result.generations[0].message.content == "ok"
