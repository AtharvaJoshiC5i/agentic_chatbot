"""LLM provider router and rate-limit helpers."""

import pytest

from app.llm.rate_limit import acquire_llm_slot, reset_rate_limiters
from app.llm.retry import invoke_with_backoff, is_rate_limit_error
from app.llm.router import is_provider_configured, list_provider_options, normalize_provider


def test_normalize_provider_defaults(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    from app.config import get_settings

    get_settings.cache_clear()
    assert normalize_provider(None) == "gemini"
    assert normalize_provider("groq") == "groq"


def test_list_providers_reflects_env(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "g")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    options = {p["id"]: p for p in list_provider_options()}
    assert options["groq"]["configured"] is True
    assert options["gemini"]["configured"] is False
    assert is_provider_configured("groq") is True


def test_rate_limit_error_detection() -> None:
    assert is_rate_limit_error(Exception("HTTP 429 Too Many Requests"))
    assert is_rate_limit_error(Exception("ResourceExhausted"))


def test_invoke_with_backoff_retries_on_429(monkeypatch) -> None:
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("429 rate limit")
        return "ok"

    monkeypatch.setattr("app.llm.retry.time.sleep", lambda _: None)
    assert invoke_with_backoff(flaky) == "ok"
    assert calls["n"] == 2


def test_acquire_llm_slot_allows_burst(monkeypatch) -> None:
    reset_rate_limiters()
    monkeypatch.setattr("app.llm.rate_limit.time.sleep", lambda _: None)
    for _ in range(3):
        acquire_llm_slot("test-cap", 3)
