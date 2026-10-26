"""Seed demo users for API authentication (Phase 6)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent / "backend"


def main() -> int:
    os.chdir(BACKEND_ROOT)
    sys.path.insert(0, str(BACKEND_ROOT))

    from app.database.session import get_session_maker
    from app.services.demo_users import ensure_demo_users

    session = get_session_maker()()
    try:
        ensure_demo_users(session)
    finally:
        session.close()

    print("Demo users ensured (passwords documented in README Phase 6).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
