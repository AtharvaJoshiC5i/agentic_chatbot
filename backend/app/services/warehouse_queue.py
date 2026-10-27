"""Warehouse work queue: analyst investigation cases awaiting receipt and inspection."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import CaseStatus, ReturnStatus
from app.models.tables import Inspection, InvestigationCase, Return

_TERMINAL_RETURN = {
    ReturnStatus.RESOLVED.value,
    ReturnStatus.CLOSED.value,
    ReturnStatus.REJECTED.value,
}
_OPEN_CASE = {
    CaseStatus.OPEN.value,
    CaseStatus.ASSIGNED.value,
    CaseStatus.IN_PROGRESS.value,
}

_STAGE_LABELS = {
    "receive": "Record receipt",
    "inspect": "Record inspection",
    "verdict": "Give refund / replacement verdict",
}


def _inspection_count(session: Session, return_id: str) -> int:
    return int(
        session.execute(
            select(func.count()).select_from(Inspection).where(Inspection.return_id == return_id)
        ).scalar_one()
    )


def _is_received(row: Return) -> bool:
    # Workflow status can be stale or represent case processing. Only the explicit
    # receipt timestamp proves that warehouse arrival was recorded.
    return row.received_date is not None


def build_warehouse_work_queue(session: Session, *, limit: int = 100) -> list[dict[str, Any]]:
    """Cases the analyst handed over that still need warehouse work: receive, inspect, then give a verdict."""
    session.expire_all()
    case_rows = list(
        session.execute(
            select(InvestigationCase)
            .where(InvestigationCase.case_status.in_(list(_OPEN_CASE)))
            .order_by(InvestigationCase.created_at.desc())
        ).scalars().all()
    )

    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for case in case_rows:
        if case.return_id in seen:
            continue
        row = session.get(Return, case.return_id)
        if row is None or row.return_status in _TERMINAL_RETURN:
            continue
        seen.add(case.return_id)
        insp = _inspection_count(session, case.return_id)
        received = _is_received(row)
        if insp == 0:
            stage = "inspect" if received else "receive"
        else:
            stage = "verdict"
        resolution = row.requested_resolution
        items.append(
            {
                "kind": "warehouse_handoff",
                "return_id": case.return_id,
                "title": case.return_id,
                "subtitle": f"Case #{case.case_id} · {resolution} · {row.return_reason.replace('_', ' ')}",
                "status": row.return_status,
                "case_id": case.case_id,
                "assigned_to": case.assigned_to,
                "priority": case.priority,
                "requested_resolution": resolution,
                "workflow_stage": stage,
                "next_action": _STAGE_LABELS[stage],
                "inspection_count": insp,
            }
        )

    return items[:limit]


def warehouse_queue_kpis(items: list[dict[str, Any]]) -> dict[str, int]:
    awaiting_receipt = sum(1 for i in items if i.get("workflow_stage") == "receive")
    awaiting_inspection = sum(1 for i in items if i.get("workflow_stage") == "inspect")
    awaiting_verdict = sum(1 for i in items if i.get("workflow_stage") == "verdict")
    return {
        "queue_total": len(items),
        "awaiting_receipt": awaiting_receipt,
        "awaiting_inspection": awaiting_inspection,
        "awaiting_verdict": awaiting_verdict,
    }
