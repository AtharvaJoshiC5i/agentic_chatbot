"""Resolve Groq vs Gemini for chat and expose provider metadata."""

from __future__ import annotations

from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import Settings, get_settings
from app.llm.gemini import get_gemini_chat_model, is_gemini_configured
from app.llm.groq import get_groq_chat_model, is_groq_configured
from app.llm.guarded import GuardedChatModel

LlmProviderId = Literal["groq", "gemini"]


def normalize_provider(value: str | None, settings: Settings | None = None) -> LlmProviderId:
    settings = settings or get_settings()
    raw = (value or settings.llm_provider or "groq").strip().lower()
    if raw not in {"groq", "gemini"}:
        raise ValueError(f"Unsupported llm_provider '{raw}'. Use groq or gemini.")
    return raw  # type: ignore[return-value]


def is_provider_configured(provider: LlmProviderId) -> bool:
    if provider == "groq":
        return is_groq_configured()
    return is_gemini_configured()


def get_chat_model(provider: LlmProviderId) -> BaseChatModel:
    if provider == "groq":
        inner = get_groq_chat_model()
        if isinstance(inner, GuardedChatModel):
            return inner
        # Per-key RPM is enforced inside GroqRotatingChatModel; outer guard adds backoff only.
        return GuardedChatModel(
            inner=inner,
            provider_id="groq",
            max_rpm=0,
        )
    return get_gemini_chat_model()


def model_name_for(provider: LlmProviderId) -> str:
    settings = get_settings()
    if provider == "groq":
        return settings.groq_model
    return settings.gemini_model.strip() or "gemini-3.5-flash-lite"


def list_provider_options() -> list[dict[str, object]]:
    settings = get_settings()
    default = normalize_provider(settings.llm_provider, settings)
    groq_keys = settings.groq_api_keys_list
    return [
        {
            "id": "groq",
            "label": "Groq",
            "configured": is_groq_configured(),
            "model": settings.groq_model,
            "max_rpm": settings.groq_effective_max_rpm,
            "max_rpm_per_key": settings.groq_max_rpm,
            "api_key_count": len(groq_keys),
            "is_default": default == "groq",
        },
        {
            "id": "gemini",
            "label": "Google Gemini",
            "configured": is_gemini_configured(),
            "model": settings.gemini_model.strip() or "gemini-3.5-flash-lite",
            "max_rpm": settings.gemini_max_rpm,
            "is_default": default == "gemini",
        },
    ]
