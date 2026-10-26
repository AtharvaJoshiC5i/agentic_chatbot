"""Groq LLM integration using the OpenAI-compatible HTTP API."""

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from openai import OpenAI

from app.config import get_settings
from app.llm.groq_rotating import GroqRotatingChatModel

GROQ_DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"


def is_groq_configured() -> bool:
    settings = get_settings()
    return bool(settings.groq_api_keys_list and settings.groq_model.strip())


@lru_cache
def get_groq_openai_client() -> OpenAI:
    """Raw OpenAI SDK client pointed at Groq (uses the primary key)."""
    settings = get_settings()
    keys = settings.groq_api_keys_list
    if not keys:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    return OpenAI(
        api_key=keys[0],
        base_url=settings.groq_base_url or GROQ_DEFAULT_BASE_URL,
    )


def get_groq_chat_model() -> BaseChatModel:
    """LangChain chat model for LangGraph tool-calling agents (multi-key when configured)."""
    settings = get_settings()
    if not is_groq_configured():
        raise RuntimeError(
            "Groq LLM is not configured. Set LLM_PROVIDER=groq, GROQ_API_KEY, and GROQ_MODEL in .env"
        )
    return GroqRotatingChatModel(
        model=settings.groq_model,
        base_url=settings.groq_base_url or GROQ_DEFAULT_BASE_URL,
        temperature=0,
        max_rpm_per_key=settings.groq_max_rpm,
    )


def groq_responses_text(prompt: str) -> str:
    """
    Optional helper using Groq's OpenAI-compatible Responses API (see Groq docs).
    The agent uses chat.completions via LangChain; this is for simple probes/health.
    """
    client = get_groq_openai_client()
    settings = get_settings()
    response = client.responses.create(
        model=settings.groq_model,
        input=prompt,
    )
    return response.output_text
