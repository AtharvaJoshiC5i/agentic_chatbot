"""Backfill return_events from structured tables for all returns."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.database.session import get_session_maker  # noqa: E402
from app.services.return_events import sync_all_return_timelines, sync_return_timeline  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync return_events timelines from SQLite sources.")
    parser.add_argument("--return-id", help="Sync a single return (e.g. R102)")
    args = parser.parse_args()

    session = get_session_maker()()
    try:
        if args.return_id:
            inserted = sync_return_timeline(session, args.return_id, commit=True)
            print(f"{args.return_id}: inserted {inserted} event(s)")
        else:
            summary = sync_all_return_timelines(session, commit=True)
            print(
                f"Synced {summary['returns']} returns; "
                f"inserted {summary['events_inserted']} new event(s)"
            )
    finally:
        session.close()


if __name__ == "__main__":
    main()
