"""Warehouse inspection queue."""

from app.services.warehouse_queue import build_warehouse_work_queue, warehouse_queue_kpis


def test_warehouse_queue_items_have_stage(populated_db) -> None:
    items = build_warehouse_work_queue(populated_db, limit=30)
    for item in items:
        assert item["kind"] == "warehouse_handoff"
        assert item["workflow_stage"] in {"receive", "inspect", "verdict"}
        assert item["case_id"] is not None
        assert item["requested_resolution"]


def test_warehouse_queue_kpis_match_items(populated_db) -> None:
    items = build_warehouse_work_queue(populated_db, limit=30)
    kpis = warehouse_queue_kpis(items)
    assert kpis["queue_total"] == len(items)
    assert kpis["awaiting_receipt"] + kpis["awaiting_inspection"] + kpis["awaiting_verdict"] == len(items)
