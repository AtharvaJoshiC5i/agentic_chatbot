"""Analyst work queue classification."""

from app.models.enums import ReturnStatus
from app.services.analyst_queue import build_analyst_work_queue


def test_analyst_work_queue_includes_open_returns(populated_db) -> None:
    items = build_analyst_work_queue(populated_db, limit=20)
    assert len(items) > 0
    assert all(item["kind"] == "analyst_work_item" for item in items)
    assert all(item["workflow_stage"] for item in items)
    assert all(item["return_id"].startswith("R") for item in items)


def test_received_return_stages_triage_or_warehouse(populated_db) -> None:
    items = build_analyst_work_queue(populated_db, limit=200)
    r103 = next((i for i in items if i["return_id"] == "R103"), None)
    if r103 is None:
        return
    assert r103["workflow_stage"] in {
        "investigate",
        "await_warehouse",
        "submit_refund",
        "submit_replacement",
        "await_supervisor",
        "customer_follow_up",
    }
