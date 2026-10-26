"""Phase 4 metadata load tests."""

from sqlalchemy import func, select

from app.documents.loader import load_document_metadata_from_manifest
from app.models.tables import DocumentMetadata


def test_load_manifest_into_database(populated_db) -> None:
    report = load_document_metadata_from_manifest(populated_db)
    assert report.ok, report.missing_files
    assert report.rows_inserted == 140

    count = populated_db.execute(select(func.count()).select_from(DocumentMetadata)).scalar_one()
    assert count == 140

    r102 = populated_db.execute(
        select(DocumentMetadata).where(DocumentMetadata.return_id == "R102")
    ).scalars().all()
    assert len(r102) >= 1
