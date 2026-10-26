"""Run F8 monitoring checks and refresh system_alerts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.database.session import get_session_maker  # noqa: E402
from app.services.monitoring import run_monitoring_checks  # noqa: E402


def main() -> None:
    session = get_session_maker()()
    try:
        result = run_monitoring_checks(session, commit=True)
        print(
            f"findings={result.findings_count} created={result.alerts_created} "
            f"resolved={result.alerts_resolved} open={result.open_alerts}"
        )
        if result.by_type:
            print("by_type:", result.by_type)
    finally:
        session.close()


if __name__ == "__main__":
    main()
