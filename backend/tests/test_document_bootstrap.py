"""Document catalog bootstrap (manifest → SQLite → optional Chroma)."""

from app.documents.loader import load_document_metadata_from_manifest
from app.rag.ingest import IngestReport
from app.services.document_bootstrap import bootstrap_documents, get_document_catalog_status


def test_manifest_load_after_populated_db(populated_db) -> None:
    report = load_document_metadata_from_manifest(populated_db)
    assert report.ok, report.missing_files
    assert report.rows_inserted > 0
    status = get_document_catalog_status(populated_db)
    assert status.metadata_count == report.rows_inserted


def test_bootstrap_documents_metadata_only(populated_db, monkeypatch) -> None:
    def _noop_ingest(_session, **kwargs):  # noqa: ANN001
        return IngestReport(documents_processed=0, chunks_indexed=0, failures=[])

    monkeypatch.setattr("app.services.document_bootstrap.ingest_all_documents", _noop_ingest)
    report = bootstrap_documents(populated_db, ingest_vectors=True, reset_index=True)
    assert report.metadata_count > 0
