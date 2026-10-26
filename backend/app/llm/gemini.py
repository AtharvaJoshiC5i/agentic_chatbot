"""Google Gemini for the LangGraph agent (OpenAI-compatible API + google-genai probe)."""

from functools import lru_cache
from typing import TYPE_CHECKING

from app.config import get_settings
from app.llm.gemini_openai_compat import GeminiChatOpenAI
from app.llm.guarded import GuardedChatModel

if TYPE_CHECKING:
    from google import genai as genai_module

# Official Gemini OpenAI compatibility layer (same client stack as Groq).
GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = "gemini-3.5-flash-lite"


def is_gemini_configured() -> bool:
    settings = get_settings()
    return bool(settings.gemini_api_key.strip())


@lru_cache
def get_gemini_client() -> "genai_module.Client":
    from google import genai

    settings = get_settings()
    if not settings.gemini_api_key.strip():
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=settings.gemini_api_key)


def get_gemini_chat_model() -> GuardedChatModel:
    """LangChain chat model via Gemini's OpenAI-compatible HTTP API (no langchain-google-genai)."""
    settings = get_settings()
    if not is_gemini_configured():
        raise RuntimeError("Gemini is not configured. Set GEMINI_API_KEY in .env")

    model_id = settings.gemini_model.strip() or GEMINI_MODEL
    inner = GeminiChatOpenAI(
        model=model_id,
        api_key=settings.gemini_api_key,
        base_url=GEMINI_OPENAI_BASE_URL,
        temperature=0,
        max_retries=0,
        # Gemini 3+ requires thought_signature replay on tool turns; streaming drops it.
        disable_streaming=True,
    )
    return GuardedChatModel(
        inner=inner,
        provider_id="gemini",
        max_rpm=settings.gemini_max_rpm,
    )


def gemini_probe_text(prompt: str = "Reply with OK.") -> str:
    """Lightweight health probe using the official google-genai SDK."""
    settings = get_settings()
    model_id = settings.gemini_model.strip() or GEMINI_MODEL
    client = get_gemini_client()
    response = client.models.generate_content(model=model_id, contents=prompt)
    return (response.text or "").strip()
