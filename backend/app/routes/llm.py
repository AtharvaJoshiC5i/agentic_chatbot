"""LLM provider discovery for UI routing."""

from fastapi import APIRouter, Depends

from app.config import get_settings
from app.llm.router import list_provider_options, normalize_provider
from app.schemas.llm import LlmProviderOption, LlmProvidersResponse
from app.security.deps import get_current_user

router = APIRouter(prefix="/llm", dependencies=[Depends(get_current_user)])


@router.get("/providers", response_model=LlmProvidersResponse)
def get_llm_providers() -> LlmProvidersResponse:
    settings = get_settings()
    default = normalize_provider(settings.llm_provider, settings)
    providers = [LlmProviderOption.model_validate(item) for item in list_provider_options()]
    return LlmProvidersResponse(default_provider=default, providers=providers)
