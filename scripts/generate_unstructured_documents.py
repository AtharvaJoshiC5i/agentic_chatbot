"""Generate the Phase 4 unstructured document corpus under data/unstructured/.

Reads backend/shopsphere.db (read-only) as the source of truth, writes PDF/DOCX/EML/TXT
documents, rebuilds data/ground_truth/document_manifest.csv and docs/README_UNSTRUCTURED.md,
then runs the verification checks. Safe to re-run: files are regenerated in place, and any
file under data/unstructured/ that the generator did not produce is reported as a failure.

Usage (from repo root):
    backend/.venv/Scripts/python scripts/generate_unstructured_documents.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from unstructured import (  # noqa: E402
    communications,
    complaints,
    inspections,
    policies,
    refurbishment,
    report,
    suppliers,
    warranties,
)
from unstructured.context import ShopSphereData  # noqa: E402
from unstructured.corpus import Corpus  # noqa: E402


def main() -> int:
    data = ShopSphereData(REPO_ROOT / "backend" / "shopsphere.db")
    corpus = Corpus(REPO_ROOT)

    # The generator owns data/unstructured/: clear it so a changed dataset cannot leave
    # orphaned files from an earlier run behind (the manifest must match the disk exactly).
    target = corpus.unstructured.resolve()
    assert target == (REPO_ROOT / "data" / "unstructured").resolve(), target
    if target.exists():
        shutil.rmtree(target)

    batches = (
        ("A: policies + warranties", lambda: (policies.build(corpus), warranties.build(corpus, data))),
        ("B: inspections", lambda: inspections.build(corpus, data)),
        ("C: complaints + supplier reports", lambda: (complaints.build(corpus, data), suppliers.build(corpus, data))),
        ("D: communications + refurbishment", lambda: (communications.build(corpus, data), refurbishment.build(corpus, data))),
    )
    for label, run in batches:
        before = len(corpus.rows)
        run()
        print(f"Batch {label}: {len(corpus.rows) - before} files")

    manifest = corpus.write_manifest()
    checks = report.verify(corpus, data)
    readme = report.write_readme(corpus, data, checks, inspections.bulk_selection(data))
    print(f"Batch E: manifest {manifest.relative_to(REPO_ROOT).as_posix()} ({len(corpus.rows)} rows), {readme.relative_to(REPO_ROOT).as_posix()}")

    failed = [c for c in checks if not c.ok]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        detail = f" ({check.detail})" if check.detail else ""
        print(f"  [{status}] {check.name}{detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
