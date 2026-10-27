"""Generate synthetic data and load it into the configured SQLite database."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent / "backend"


def main() -> int:
    os.chdir(BACKEND_ROOT)
    sys.path.insert(0, str(BACKEND_ROOT))

    from app.config import get_settings
    from app.database.session import get_session_maker
    from app.documents.loader import load_document_metadata_from_manifest
    from app.synthetic.generator import generate_synthetic_data
    from app.synthetic.ground_truth import write_ground_truth_files
    from app.synthetic.loader import load_bundle
    from app.synthetic.serial_repair import align_single_quantity_product_unit_serials
    from app.synthetic.validate import validate_loaded_database

    settings = get_settings()
    settings.ensure_runtime_directories()

    bundle = generate_synthetic_data()
    write_ground_truth_files()

    from app.rag.ingest import ingest_all_documents
    from app.rag.store import collection_document_count

    session = get_session_maker()()
    ingest_report = None
    try:
        load_bundle(session, bundle)
        aligned = align_single_quantity_product_unit_serials(session)
        if aligned:
            print(f"Aligned {aligned} product_unit serial(s) with order-line purchased serials.")
        report = validate_loaded_database(session)
        document_report = load_document_metadata_from_manifest(session)
        if report.ok and document_report.ok:
            ingest_report = ingest_all_documents(session, reset_index=True)
    finally:
        session.close()

    if not report.ok:
        print("Validation failed:", file=sys.stderr)
        for error in report.errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    if not document_report.ok:
        print("Document metadata load failed:", file=sys.stderr)
        for path in document_report.missing_files:
            print(f"  missing file: {path}", file=sys.stderr)
        for return_id in document_report.invalid_return_ids:
            print(f"  invalid return_id: {return_id}", file=sys.stderr)
        for product_id in document_report.invalid_product_ids:
            print(f"  invalid product_id: {product_id}", file=sys.stderr)
        return 1

    for warning in report.warnings:
        print(f"Warning: {warning}")

    if ingest_report and ingest_report.failures:
        print("Vector ingest warnings:", file=sys.stderr)
        for failure in ingest_report.failures[:10]:
            print(f"  - {failure}", file=sys.stderr)

    print(f"Loaded structured data into {settings.sqlite_database_path}")
    print(f"Returns: {len(bundle.returns)} | Inspections: {len(bundle.inspections)} | Refunds: {len(bundle.refunds)}")
    print(f"Documents: {document_report.rows_inserted}")
    if ingest_report:
        print(
            f"Chroma: {ingest_report.chunks_indexed} chunks from {ingest_report.documents_processed} files "
            f"(collection count={collection_document_count()})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
