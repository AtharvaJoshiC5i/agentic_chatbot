"""Schemas for the read-only data browser API."""

from pydantic import BaseModel, Field


class DataBrowserOverview(BaseModel):
    structured_table_count: int
    structured_row_count: int
    document_count: int
    document_types: list[str] = Field(default_factory=list)


class StructuredTableSummary(BaseModel):
    name: str
    label: str
    row_count: int
    column_count: int


class StructuredTableListResponse(BaseModel):
    tables: list[StructuredTableSummary]


class StructuredTableRowsResponse(BaseModel):
    table_name: str
    label: str
    columns: list[str]
    rows: list[dict[str, str]]
    total: int
    limit: int
    offset: int


class DocumentBrowserItem(BaseModel):
    document_id: int
    filename: str
    document_type: str
    return_id: str | None
    product_id: str | None
    file_path: str
    file_kind: str
    created_at: str
    policy_version: str | None = None
    effective_date: str | None = None


class DocumentBrowserListResponse(BaseModel):
    items: list[DocumentBrowserItem]
    total: int
    limit: int
    offset: int
    document_types: list[str] = Field(default_factory=list)
