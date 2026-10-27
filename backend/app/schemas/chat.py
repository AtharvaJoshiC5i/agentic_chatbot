"""Chat API schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field

LlmProviderChoice = Literal["groq", "gemini", "nvidia"]


class ChatTurn(BaseModel):
    role: str = Field(description="user or assistant")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None
    return_id: str | None = None
    history: list[ChatTurn] = Field(default_factory=list)
    llm_provider: LlmProviderChoice | None = Field(
        default=None,
        description="groq, gemini, or nvidia; omit to use server default (LLM_PROVIDER).",
    )


class AgentStepOut(BaseModel):
    index: int
    kind: str
    title: str
    status: str = "completed"
    detail: str | None = None
    tool: str | None = None
    input: str | None = None
    output: str | None = None


class DocumentSourceOut(BaseModel):
    document_id: int
    filename: str
    file_path: str
    page_or_section: str | None = None
    passage: str
    relevance_score: float | None = None
    file_kind: str


class StructuredEvidenceOut(BaseModel):
    evidence_id: str
    source_tool: str
    table_name: str
    title: str
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, str]] = Field(default_factory=list)
    record: dict[str, Any] | None = None


class SupportingEvidenceOut(BaseModel):
    structured: list[StructuredEvidenceOut] = Field(default_factory=list)
    documents: list[DocumentSourceOut] = Field(default_factory=list)


class ChatResponse(BaseModel):
    conversation_id: str | None
    return_id: str | None
    inferred_return_id: str | None = None
    final_response: str
    tool_events: list[dict[str, Any]] = Field(default_factory=list)
    agent_steps: list[AgentStepOut] = Field(default_factory=list)
    supporting_evidence: SupportingEvidenceOut | None = None
    document_sources: list[DocumentSourceOut] = Field(default_factory=list)
    visuals: list[dict[str, Any]] = Field(default_factory=list)
    llm_provider: str
    llm_model: str
