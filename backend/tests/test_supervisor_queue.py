"""Supervisor approval queue."""

from app.services.supervisor_queue import build_supervisor_approval_queue, supervisor_queue_kpis


def test_supervisor_queue_kpis_consistent(populated_db) -> None:
    items = build_supervisor_approval_queue(populated_db, query_limit=30)
    kpis = supervisor_queue_kpis(items, shown=len(items))
    assert kpis["queue_total"] == len(items)
    assert kpis["pending_refunds"] + kpis["pending_replacements"] <= len(items)
