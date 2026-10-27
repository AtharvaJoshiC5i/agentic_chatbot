"""NVIDIA NIM chat model using the OpenAI-compatible API."""

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.llm.guarded import GuardedChatModel

NVIDIA_DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_DEFAULT_MODEL = "z-ai/glm-5.3-flash"


def is_nvidia_configured() -> bool:
    settings = get_settings()
    return bool(settings.nvidia_api_key.strip() and settings.nvidia_model.strip())


@lru_cache
def get_nvidia_chat_model() -> BaseChatModel:
    settings = get_settings()
    if not is_nvidia_configured():
        raise RuntimeError("NVIDIA NIM is not configured. Set NVIDIA_API_KEY in the repo-root .env")

    inner = ChatOpenAI(
        model=settings.nvidia_model.strip() or NVIDIA_DEFAULT_MODEL,
        api_key=settings.nvidia_api_key,
        base_url=settings.nvidia_base_url.strip() or NVIDIA_DEFAULT_BASE_URL,
        temperature=0,
        max_retries=0,
        streaming=True,
    )
    return GuardedChatModel(
        inner=inner,
        provider_id="nvidia",
        max_rpm=settings.nvidia_max_rpm,
    )
