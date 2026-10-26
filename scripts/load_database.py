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
    from app.synthetic.generator import generate_synthetic_data
    from app.synthetic.ground_truth import write_ground_truth_files
    from app.synthetic.loader import load_bundle
    from app.synthetic.validate import validate_loaded_database

    settings = get_settings()
    settings.ensure_runtime_directories()

    bundle = generate_synthetic_data()
    write_ground_truth_files()

    session = get_session_maker()()
    try:
        load_bundle(session, bundle)
        report = validate_loaded_database(session)
    finally:
        session.close()

    if not report.ok:
        print("Validation failed:", file=sys.stderr)
        for error in report.errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    for warning in report.warnings:
        print(f"Warning: {warning}")

    print(f"Loaded structured data into {settings.sqlite_database_path}")
    print(f"Returns: {len(bundle.returns)} | Inspections: {len(bundle.inspections)} | Refunds: {len(bundle.refunds)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
