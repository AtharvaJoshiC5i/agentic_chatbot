"""Load document catalog (SQLite) and vector index (Chroma) for unstructured data."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.documents.loader import MANIFEST_PATH, ManifestLoadReport, load_document_metadata_from_manifest
from app.models.tables import DocumentMetadata, Return
from app.rag.ingest import IngestReport, ingest_all_documents
from app.rag.store import collection_document_count

logger = logging.getLogger(__name__)


@dataclass
class DocumentCatalogStatus:
    manifest_exists: bool
    manifest_path: str
    return_count: int
    metadata_count: int
    chroma_chunk_count: int
    ready: bool
    message: str


@dataclass
class DocumentBootstrapReport:
    ok: bool
    metadata: ManifestLoadReport | None = None
    ingest: IngestReport | None = None
    metadata_count: int = 0
    chroma_chunk_count: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "metadata_count": self.metadata_count,
            "chroma_chunk_count": self.chroma_chunk_count,
            "errors": self.errors,
            "manifest_rows_inserted": self.metadata.rows_inserted if self.metadata else 0,
            "documents_processed": self.ingest.documents_processed if self.ingest else 0,
            "chunks_indexed": self.ingest.chunks_indexed if self.ingest else 0,
            "ingest_failures": self.ingest.failures if self.ingest else [],
        }


def get_document_catalog_status(session: Session) -> DocumentCatalogStatus:
    metadata_count = int(
        session.execute(select(func.count()).select_from(DocumentMetadata)).scalar_one()
    )
    return_count = int(session.execute(select(func.count()).select_from(Return)).scalar_one())
    chroma_count = 0
    try:
        chroma_count = collection_document_count()
    except Exception:  # noqa: BLE001 — Chroma may be uninitialized
        chroma_count = 0

    manifest_exists = MANIFEST_PATH.is_file()
    ready = metadata_count > 0 and chroma_count > 0

    if not manifest_exists:
        message = (
            "Document manifest missing. Run: python scripts/generate_unstructured_documents.py"
        )
    elif return_count == 0:
        message = "No returns in database. Run: python scripts/load_database.py"
    elif metadata_count == 0:
        message = "Document catalog empty. Run bootstrap (API or scripts/bootstrap_documents.py)."
    elif chroma_count == 0:
        message = "Documents in SQLite but vector index empty. Re-run bootstrap with ingest."
    else:
        message = f"{metadata_count} documents cataloged, {chroma_count} chunks indexed."

    return DocumentCatalogStatus(
        manifest_exists=manifest_exists,
        manifest_path=str(MANIFEST_PATH),
        return_count=return_count,
        metadata_count=metadata_count,
        chroma_chunk_count=chroma_count,
        ready=ready,
        message=message,
    )


def bootstrap_documents(
    session: Session,
    *,
    ingest_vectors: bool = True,
    reset_index: bool = True,
) -> DocumentBootstrapReport:
    """Load document_metadata from manifest, then optionally embed into Chroma."""
    errors: list[str] = []
    status = get_document_catalog_status(session)

    if not status.manifest_exists:
        return DocumentBootstrapReport(
            ok=False,
            errors=[status.message],
        )

    if status.return_count == 0:
        return DocumentBootstrapReport(
            ok=False,
            errors=[status.message],
        )

    try:
        metadata_report = load_document_metadata_from_manifest(session)
    except FileNotFoundError as exc:
        return DocumentBootstrapReport(ok=False, errors=[str(exc)])

    if not metadata_report.ok:
        if metadata_report.missing_files:
            errors.append(f"{len(metadata_report.missing_files)} manifest file(s) missing on disk")
            errors.extend(metadata_report.missing_files[:5])
            if len(metadata_report.missing_files) > 5:
                errors.append("…")
        if metadata_report.invalid_return_ids:
            errors.append(
                "Manifest return_id(s) not in DB (run load_database.py): "
                + ", ".join(sorted(set(metadata_report.invalid_return_ids))[:8])
            )
        if metadata_report.invalid_product_ids:
            errors.append(
                "Manifest product_id(s) not in DB: "
                + ", ".join(sorted(set(metadata_report.invalid_product_ids))[:8])
            )
        return DocumentBootstrapReport(ok=False, metadata=metadata_report, errors=errors)

    ingest_report: IngestReport | None = None
    if ingest_vectors:
        ingest_report = ingest_all_documents(session, reset_index=reset_index)
        if ingest_report.failures:
            errors.extend(ingest_report.failures[:10])
            if len(ingest_report.failures) > 10:
                errors.append(f"… and {len(ingest_report.failures) - 10} more ingest failures")

    metadata_count = int(
        session.execute(select(func.count()).select_from(DocumentMetadata)).scalar_one()
    )
    chroma_count = collection_document_count() if ingest_vectors else status.chroma_chunk_count
    ok = metadata_count > 0 and (not ingest_vectors or chroma_count > 0) and not errors

    return DocumentBootstrapReport(
        ok=ok,
        metadata=metadata_report,
        ingest=ingest_report,
        metadata_count=metadata_count,
        chroma_chunk_count=chroma_count,
        errors=errors,
    )


def ensure_documents_bootstrapped_if_empty(session: Session) -> DocumentBootstrapReport | None:
    """When catalog is empty but returns exist, load metadata + index once (dev convenience)."""
    status = get_document_catalog_status(session)
    if status.metadata_count > 0:
        if status.chroma_chunk_count == 0:
            logger.warning(
                "document_metadata has %s rows but Chroma is empty; run scripts/bootstrap_documents.py",
                status.metadata_count,
            )
        return None
    if not status.manifest_exists or status.return_count == 0:
        logger.warning("Documents not bootstrapped: %s", status.message)
        return None

    logger.info("Document catalog empty — bootstrapping from %s", MANIFEST_PATH)
    report = bootstrap_documents(session, ingest_vectors=True, reset_index=True)
    if report.ok:
        logger.info(
            "Document bootstrap OK: %s metadata rows, %s Chroma chunks",
            report.metadata_count,
            report.chroma_chunk_count,
        )
    else:
        logger.error("Document bootstrap failed: %s", "; ".join(report.errors))
    return report
