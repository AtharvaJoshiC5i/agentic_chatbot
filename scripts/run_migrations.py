"""Apply Alembic migrations to the configured SQLite database."""

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent / "backend"


def main() -> int:
    ini_path = BACKEND_ROOT / "alembic.ini"
    if not ini_path.exists():
        print(f"Alembic config not found: {ini_path}", file=sys.stderr)
        return 1

    os.chdir(BACKEND_ROOT)
    sys.path.insert(0, str(BACKEND_ROOT))

    from alembic import command
    from alembic.config import Config

    config = Config(str(ini_path))
    command.upgrade(config, "head")
    print("Migrations applied successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
