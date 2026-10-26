"""Document preview and file download for chat citations."""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.documents import DocumentPreviewResponse
from app.security.deps import CurrentUser, get_current_user
from app.services.document_preview import build_document_preview, get_document_metadata, resolve_document_path
from app.services.document_render import build_rendered_html_preview

router = APIRouter(prefix="/documents", dependencies=[Depends(get_current_user)])


@router.get("/{document_id}/preview", response_model=DocumentPreviewResponse)
def get_document_preview(
    document_id: int,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> DocumentPreviewResponse:
    payload = build_document_preview(db, document_id)
    return DocumentPreviewResponse.model_validate(payload)


@router.get("/{document_id}/preview-html", response_class=HTMLResponse)
def get_document_preview_html(
    document_id: int,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> HTMLResponse:
    """Full-page HTML preview for .eml / .docx (and .txt)."""
    html_content = build_rendered_html_preview(db, document_id)
    return HTMLResponse(content=html_content)


@router.get("/{document_id}/file")
def get_document_file(
    document_id: int,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> FileResponse:
    row = get_document_metadata(db, document_id)
    path = resolve_document_path(row)
    from app.services.document_preview import MIME_BY_KIND, _file_kind

    kind = _file_kind(row.filename)
    return FileResponse(
        path,
        media_type=MIME_BY_KIND.get(kind, "application/octet-stream"),
        filename=row.filename,
    )
