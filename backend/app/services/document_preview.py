"""Load document text for in-app preview."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import PROJECT_ROOT
from app.models.tables import DocumentMetadata
from app.rag.extract import extract_document

MIME_BY_KIND = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "eml": "message/rfc822",
    "txt": "text/plain",
}


def _file_kind(filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext or "unknown"


def get_document_metadata(session: Session, document_id: int) -> DocumentMetadata:
    row = session.execute(
        select(DocumentMetadata).where(DocumentMetadata.document_id == document_id)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return row


def resolve_document_path(row: DocumentMetadata) -> Path:
    absolute = (PROJECT_ROOT / row.file_path).resolve()
    root = PROJECT_ROOT.resolve()
    if not str(absolute).startswith(str(root)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document path")
    if not absolute.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file missing on disk")
    return absolute


def build_document_preview(session: Session, document_id: int) -> dict:
    row = get_document_metadata(session, document_id)
    path = resolve_document_path(row)
    kind = _file_kind(row.filename)
    try:
        extracted = extract_document(path)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    segments = [
        {"page": segment.page, "section": segment.section, "text": segment.text}
        for segment in extracted.segments
    ]
    return {
        "document_id": row.document_id,
        "filename": row.filename,
        "file_path": row.file_path,
        "file_kind": kind,
        "mime_type": MIME_BY_KIND.get(kind, "application/octet-stream"),
        "segments": segments,
        "full_text": extracted.full_text,
    }
