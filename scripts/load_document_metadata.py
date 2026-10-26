"""Load data/ground_truth/document_manifest.csv into SQLite document_metadata."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent / "backend"


def main() -> int:
    os.chdir(BACKEND_ROOT)
    sys.path.insert(0, str(BACKEND_ROOT))

    from app.database.session import get_session_maker
    from app.documents.loader import load_document_metadata_from_manifest

    session = get_session_maker()()
    try:
        report = load_document_metadata_from_manifest(session)
    finally:
        session.close()

    if not report.ok:
        print("Metadata load failed:", file=sys.stderr)
        for path in report.missing_files:
            print(f"  missing file: {path}", file=sys.stderr)
        for return_id in report.invalid_return_ids:
            print(f"  invalid return_id: {return_id}", file=sys.stderr)
        for product_id in report.invalid_product_ids:
            print(f"  invalid product_id: {product_id}", file=sys.stderr)
        return 1

    print(f"Loaded {report.rows_inserted} document_metadata rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
