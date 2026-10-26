"""Read-only data browser (structured SQLite tables + document catalog)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.data_browser import (
    DataBrowserOverview,
    DocumentBrowserListResponse,
    StructuredTableListResponse,
    StructuredTableRowsResponse,
)
from app.security.deps import CurrentUser, get_current_user
from app.services.data_browser import get_overview, get_structured_table_rows, list_documents, list_structured_tables

router = APIRouter(prefix="/data-browser", dependencies=[Depends(get_current_user)])


@router.get("/overview", response_model=DataBrowserOverview)
def data_browser_overview(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> DataBrowserOverview:
    return DataBrowserOverview.model_validate(get_overview(db))


@router.get("/tables", response_model=StructuredTableListResponse)
def data_browser_tables(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> StructuredTableListResponse:
    tables = list_structured_tables(db)
    return StructuredTableListResponse(tables=tables)


@router.get("/tables/{table_name}/rows", response_model=StructuredTableRowsResponse)
def data_browser_table_rows(
    table_name: str,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> StructuredTableRowsResponse:
    payload = get_structured_table_rows(db, table_name, limit=limit, offset=offset)
    return StructuredTableRowsResponse.model_validate(payload)


@router.get("/documents", response_model=DocumentBrowserListResponse)
def data_browser_documents(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    document_type: str | None = None,
    return_id: str | None = None,
    search: str | None = None,
) -> DocumentBrowserListResponse:
    payload = list_documents(
        db,
        limit=limit,
        offset=offset,
        document_type=document_type,
        return_id=return_id,
        search=search,
    )
    return DocumentBrowserListResponse.model_validate(payload)
