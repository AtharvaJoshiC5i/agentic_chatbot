"""Validate structured data already loaded in SQLite."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent / "backend"


def main() -> int:
    os.chdir(BACKEND_ROOT)
    sys.path.insert(0, str(BACKEND_ROOT))

    from app.database.session import get_session_maker
    from app.synthetic.validate import validate_loaded_database

    session = get_session_maker()()
    try:
        report = validate_loaded_database(session)
    finally:
        session.close()

    if report.warnings:
        print("Warnings:")
        for warning in report.warnings:
            print(f"  - {warning}")

    if not report.ok:
        print("Validation failed:", file=sys.stderr)
        for error in report.errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Structured data validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
