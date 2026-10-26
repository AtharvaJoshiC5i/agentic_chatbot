"""Document preview API schemas."""

from pydantic import BaseModel, Field


class DocumentTextSegment(BaseModel):
    page: int | None = None
    section: str | None = None
    text: str


class DocumentPreviewResponse(BaseModel):
    document_id: int
    filename: str
    file_path: str
    file_kind: str
    mime_type: str
    segments: list[DocumentTextSegment] = Field(default_factory=list)
    full_text: str
