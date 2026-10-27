"""Load document_manifest into SQLite and index unstructured files into ChromaDB.

Requires structured returns/products already in the database (from load_database.py).
Does not wipe returns — only refreshes document_metadata and the vector index.

Usage (from repo root):
  backend\\.venv\\Scripts\\python scripts/bootstrap_documents.py
"""

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
    from app.services.document_bootstrap import bootstrap_documents, get_document_catalog_status

    settings = get_settings()
    settings.ensure_runtime_directories()

    session = get_session_maker()()
    try:
        before = get_document_catalog_status(session)
        print(f"Before: {before.message}")
        report = bootstrap_documents(session, ingest_vectors=True, reset_index=True)
    finally:
        session.close()

    if not report.ok:
        print("Bootstrap failed:", file=sys.stderr)
        for err in report.errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(
        f"OK: {report.metadata_count} documents in SQLite, "
        f"{report.chroma_chunk_count} chunks in Chroma ({settings.chroma_directory})"
    )
    if report.ingest and report.ingest.failures:
        print(f"Warning: {len(report.ingest.failures)} ingest failure(s) — see stderr above")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
