"""Run Phase 14 ground-truth evaluation and print a summary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import func, select

from app.database.session import get_session_maker  # noqa: E402
from app.eval.harness import run_full_eval  # noqa: E402
from app.models.tables import Return  # noqa: E402
from app.synthetic.generator import generate_synthetic_data  # noqa: E402
from app.synthetic.loader import load_bundle  # noqa: E402


def main() -> None:
    session = get_session_maker()()
    try:
        count = session.execute(select(func.count()).select_from(Return)).scalar_one()
        if int(count) == 0:
            load_bundle(session, generate_synthetic_data())

        report = run_full_eval(session)
        print(json.dumps(report.to_dict(), indent=2, default=str))
        if not report.passed:
            sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
