"""Schemas for the read-only data browser API."""

from pydantic import BaseModel, Field


class DataBrowserOverview(BaseModel):
    structured_table_count: int
    structured_row_count: int
    document_count: int
    document_types: list[str] = Field(default_factory=list)
    database_url: str
    database_file: str | None = None
    database_file_exists: bool = False
    documents_ready: bool = False
    documents_status_message: str = ""


class DocumentCatalogStatusOut(BaseModel):
    manifest_exists: bool
    manifest_path: str
    return_count: int
    metadata_count: int
    chroma_chunk_count: int
    ready: bool
    message: str


class DocumentBootstrapResponse(BaseModel):
    ok: bool
    metadata_count: int
    chroma_chunk_count: int
    errors: list[str] = Field(default_factory=list)
    manifest_rows_inserted: int = 0
    documents_processed: int = 0
    chunks_indexed: int = 0
    ingest_failures: list[str] = Field(default_factory=list)


class StructuredTableSummary(BaseModel):
    name: str
    label: str
    row_count: int
    column_count: int


class StructuredTableListResponse(BaseModel):
    tables: list[StructuredTableSummary]


class StructuredRowMatch(BaseModel):
    column: str
    value: str


class StructuredTableRowsResponse(BaseModel):
    table_name: str
    label: str
    columns: list[str]
    rows: list[dict[str, str]]
    total: int
    limit: int
    offset: int
    matched: StructuredRowMatch | None = None


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
