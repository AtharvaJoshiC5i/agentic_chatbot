"""Structured visuals for chat answers, built from the database (never from model text).

Each tool the agent ran maps to at most one visual per return. Values are re-read from
SQLite and the deterministic services, so a visual can never show a number the model
invented. The frontend renders these specs with fixed components.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

from app.database.session import get_session_maker
from app.investigation.investigation import run_investigation
from app.services.return_workflow import build_return_workflow_snapshot
from app.models.tables import ActionRequest, Inspection, OrderItem, Refund, Return
from app.services.recovery_optimizer import optimize_recovery

logger = logging.getLogger(__name__)

TOOL_TO_VISUALS: dict[str, tuple[str, ...]] = {
    "run_return_investigation": ("investigation", "return_window"),
    "get_return_workflow_status": ("workflow",),
    "get_return_details": ("workflow",),
    "get_inspection_results": ("evidence", "workflow"),
    "search_inspection_reports": ("evidence",),
    "get_recovery_options": ("recovery",),
    "get_recovery_recommendation": ("recovery",),
    "get_refund_status": ("refund_ledger",),
    "submit_refund_request": ("actions",),
    "submit_create_investigation_case": ("actions",),
    "submit_repair_recovery_task": ("actions",),
    "submit_refurbishment_task": ("actions",),
    "submit_inspection_task": ("actions",),
    "approve_action_request": ("actions",),
    "get_action_request_status": ("actions",),
    "list_actions_for_return": ("actions",),
    "execute_action_request": ("actions", "refund_ledger"),
    "approve_refund_record": ("refund_ledger",),
    "execute_refund_payout": ("refund_ledger",),
    "list_refunds_awaiting_approval": ("refund_queue",),
    "list_open_investigation_cases": ("case_queue",),
}
MAX_VISUALS = 4


def _inr(paise: int | None) -> float | None:
    return None if paise is None else round(paise / 100, 2)


def _investigation(session, return_id: str) -> dict | None:
    report = run_investigation(session, return_id)
    if report is None:
        return None
    return {
        "type": "investigation",
        "return_id": return_id,
        "outcome": report.f4_outcome,
        "signal": report.f2_signal,
        "recommended_actions": report.recommended_actions,
        "checks": [{"title": c.title, "status": str(c.status), "summary": c.summary} for c in report.checks],
        "source": "Investigation engine (12 deterministic checks)",
    }


def _return_window(session, return_id: str) -> dict | None:
    report = run_investigation(session, return_id)
    if report is None:
        return None
    policy = report.f3_policy
    return {
        "type": "return_window",
        "return_id": return_id,
        "days_after_delivery": policy.days_after_delivery,
        "window_days": policy.return_window_days,
        "within_window": policy.within_return_window,
        "category": policy.product_category,
        "delivered": str(policy.delivery_date)[:10] if policy.delivery_date else None,
        "requested": str(policy.return_request_date)[:10] if policy.return_request_date else None,
        "warranty_months": policy.warranty_months,
        "within_warranty": policy.within_warranty_period,
        "source": "Return policy check (delivery and request dates from SQLite)",
    }


def _workflow(session, return_id: str) -> dict | None:
    if not return_id:
        return None
    snap = build_return_workflow_snapshot(session, return_id)
    if snap.get("error"):
        return None
    return {
        "type": "workflow",
        "return_id": return_id,
        "status_summary": snap.get("status_summary"),
        "warehouse_work_complete": snap.get("warehouse_work_complete"),
        "inspection_count": snap.get("inspection_count"),
        "analyst_workflow_stage": snap.get("analyst_workflow_stage"),
        "analyst_next_action": snap.get("analyst_next_action"),
        "active_case": snap.get("active_case"),
        "source": "Return workflow (live database)",
    }


def _evidence(session, return_id: str) -> dict | None:
    ret = session.get(Return, return_id)
    if ret is None:
        return None
    item = session.get(OrderItem, ret.order_item_id)
    rows = session.execute(select(Inspection).where(Inspection.return_id == return_id).order_by(Inspection.inspection_id)).scalars().all()
    purchased = item.purchased_serial_number if item else None
    return {
        "type": "evidence",
        "return_id": return_id,
        "purchased_serial": purchased,
        "inspections": [
            {
                "inspection_id": i.inspection_id,
                "date": str(i.inspection_date)[:10],
                "returned_serial": i.returned_serial_number,
                "serial_match": None if not (purchased and i.returned_serial_number) else purchased == i.returned_serial_number,
                "condition": i.product_condition,
                "defect_verified": bool(i.defect_verified),
                "accessories_complete": bool(i.accessories_complete),
                "result": i.inspection_result,
            }
            for i in rows
        ],
        "source": "Order line and warehouse inspection records",
    }


def _recovery(session, return_id: str) -> dict | None:
    rec = optimize_recovery(session, return_id)
    return {
        "type": "recovery",
        "return_id": return_id,
        "unsafe": rec.unsafe_product,
        "recommended_method": rec.recommended_method,
        "requires_approval": rec.requires_approval,
        "rationale": rec.rationale,
        "options": [
            {
                "method": o.recovery_method,
                "net_inr": _inr(o.expected_net_recovery_paise),
                "feasibility": o.feasibility_status,
                "eligible": o.eligible,
                "reason": o.exclusion_reason,
            }
            for o in rec.ranked_options
        ],
        "source": "Recovery optimiser (recovery_options table)",
    }


def _refund_ledger(session, return_id: str) -> dict | None:
    rows = session.execute(select(Refund).where(Refund.return_id == return_id).order_by(Refund.refund_id)).scalars().all()
    return {
        "type": "refund_ledger",
        "return_id": return_id,
        "has_completed": any(r.refund_status == "completed" for r in rows),
        "refunds": [
            {"refund_id": r.refund_id, "amount_inr": _inr(r.refund_amount), "status": r.refund_status,
             "approval": r.approval_status, "processed": str(r.processed_date)[:10] if r.processed_date else None}
            for r in rows
        ],
        "source": "Refund ledger",
    }


def _actions(session, return_id: str) -> dict | None:
    rows = session.execute(select(ActionRequest).where(ActionRequest.return_id == return_id).order_by(ActionRequest.action_id)).scalars().all()
    if not rows:
        return None
    return {
        "type": "actions",
        "return_id": return_id,
        "actions": [
            {"action_id": a.action_id, "action_type": a.action_type, "requested_by": a.requested_by,
             "approval": a.approval_status, "execution": a.execution_status}
            for a in rows
        ],
        "source": "Action requests (approval workflow)",
    }


def _refund_queue(session, _return_id: str | None) -> dict:
    rows = session.execute(
        select(Refund).where(Refund.refund_status == "requested", Refund.approval_status == "pending").order_by(Refund.refund_amount.desc())
    ).scalars().all()
    return {
        "type": "refund_queue",
        "count": len(rows),
        "total_inr": _inr(sum(r.refund_amount for r in rows)),
        "rows": [{"refund_id": r.refund_id, "return_id": r.return_id, "amount_inr": _inr(r.refund_amount)} for r in rows[:10]],
        "thresholds_inr": {"analyst": 10_000, "supervisor": 50_000},
        "source": "Refund ledger (pending approval)",
    }


def _case_queue(session, _return_id: str | None) -> dict:
    from app.tools.portfolio_tools import list_open_investigation_case_rows

    cases = list_open_investigation_case_rows(session, overdue_only=False)
    return {
        "type": "case_queue",
        "count": len(cases),
        "overdue": sum(1 for c in cases if c["overdue"]),
        "rows": cases[:10],
        "source": "Investigation cases",
    }


BUILDERS = {
    "investigation": _investigation,
    "return_window": _return_window,
    "workflow": _workflow,
    "evidence": _evidence,
    "recovery": _recovery,
    "refund_ledger": _refund_ledger,
    "actions": _actions,
    "refund_queue": _refund_queue,
    "case_queue": _case_queue,
}
PORTFOLIO = {"refund_queue", "case_queue"}


def build_visuals(tool_events: list[dict[str, Any]], focus_return: str | None) -> list[dict[str, Any]]:
    """Return visual specs for the tools that ran, deduplicated, most relevant first."""
    session = get_session_maker()()
    wanted: list[tuple[str, str | None]] = []
    for event in tool_events:
        args = event.get("args") or {}
        rid = str(args.get("return_id") or focus_return or "").upper() or None
        for kind in TOOL_TO_VISUALS.get(event.get("tool") or "", ()):
            key = (kind, None if kind in PORTFOLIO else rid)
            if key not in wanted and (kind in PORTFOLIO or rid):
                wanted.append(key)
    visuals: list[dict[str, Any]] = []
    try:
        for kind, rid in wanted[:MAX_VISUALS]:
            try:
                spec = BUILDERS[kind](session, rid)
            except Exception:  # noqa: BLE001
                logger.exception("visual %s for %s failed", kind, rid)
                continue
            if spec:
                visuals.append(spec)
    finally:
        session.close()
    return visuals
