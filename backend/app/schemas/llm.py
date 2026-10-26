"""LLM provider router schemas."""

from pydantic import BaseModel, Field


class LlmProviderOption(BaseModel):
    id: str
    label: str
    configured: bool
    model: str
    max_rpm: int
    is_default: bool = False


class LlmProvidersResponse(BaseModel):
    default_provider: str
    providers: list[LlmProviderOption] = Field(default_factory=list)
