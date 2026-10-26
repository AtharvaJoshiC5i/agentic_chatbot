"""Extract, chunk, embed, and index all document_metadata rows into ChromaDB."""

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
    from app.rag.ingest import ingest_all_documents
    from app.rag.store import collection_document_count

    settings = get_settings()
    settings.ensure_runtime_directories()

    session = get_session_maker()()
    try:
        report = ingest_all_documents(session, reset_index=True)
    finally:
        session.close()

    if report.failures:
        print("Ingest completed with failures:", file=sys.stderr)
        for failure in report.failures:
            print(f"  - {failure}", file=sys.stderr)

    print(
        f"Indexed {report.chunks_indexed} chunks from {report.documents_processed} documents. "
        f"Chroma count={collection_document_count()} path={settings.chroma_directory}"
    )
    return 1 if report.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
