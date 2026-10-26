"""LLM clients: Groq (OpenAI-compatible) and Google Gemini."""

from app.llm.gemini import get_gemini_chat_model, is_gemini_configured
from app.llm.groq import get_groq_chat_model, get_groq_openai_client, is_groq_configured
from app.llm.router import get_chat_model, list_provider_options, normalize_provider

__all__ = [
    "get_chat_model",
    "get_gemini_chat_model",
    "get_groq_chat_model",
    "get_groq_openai_client",
    "is_gemini_configured",
    "is_groq_configured",
    "list_provider_options",
    "normalize_provider",
]
