"""Unified return workflow snapshot (all personas read the same DB truth)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import CustomerNotification, Refund, ReplacementRequest, Return
from app.services.analyst_queue import (
    STAGE_LABELS,
    classify_return_workflow,
    supervisor_pending_for_return,
)
from app.services.handoff import get_latest_verdict, verdict_to_dict
from app.services.notifications import notification_to_dict
from app.services.replacements import replacement_to_dict
from app.services.warehouse_handoff import get_warehouse_handoff_status

# Who has to act next, per analyst stage.
_OWNER = {
    "investigate": "returns_analyst",
    "await_warehouse": "warehouse_manager",
    "submit_refund": "returns_analyst",
    "submit_replacement": "returns_analyst",
    "decline_request": "returns_analyst",
    "await_supervisor": "returns_supervisor",
    "customer_follow_up": "returns_analyst",
}


def _status_summary(*, stage: str | None, return_status: str, requested_resolution: str, verdict: dict | None) -> str:
    if stage == "investigate":
        return "Returns analyst should investigate against policy and open an investigation case."
    if stage == "await_warehouse":
        return "With the warehouse: receive, inspect and give a refund/replacement verdict."
    if stage == "submit_refund":
        return "Warehouse says the refund can be performed. Returns analyst should submit it to the supervisor."
    if stage == "submit_replacement":
        return "Warehouse says the replacement can be performed (stock available). Returns analyst should submit it."
    if stage == "decline_request":
        why = (verdict or {}).get("notes") or "no reason given"
        return f"Warehouse says this cannot be performed ({why}). Returns analyst should decline and notify the customer."
    if stage == "await_supervisor":
        return "Submitted to the supervisor; awaiting a decision."
    if stage == "customer_follow_up":
        return "Decision recorded. Returns analyst should review and send the customer email."
    if return_status == "closed":
        return "Closed. The customer has been notified."
    return f"Return status is {return_status.replace('_', ' ')}; requested {requested_resolution}."


def build_return_workflow_snapshot(session: Session, return_id: str) -> dict[str, Any]:
    """Single workflow view for agents, dashboards, and APIs (always fresh ORM read)."""
    session.expire_all()
    rid = return_id.strip().upper()
    row = session.get(Return, rid)
    if row is None:
        return {"error": "not_found", "message": "Return not found", "return_id": rid}

    handoff = get_warehouse_handoff_status(session, rid)
    analyst = classify_return_workflow(session, rid)
    stage = analyst.get("analyst_workflow_stage") if analyst else None
    verdict = verdict_to_dict(get_latest_verdict(session, rid))
    insp_count = int(handoff.get("inspection_count") or 0)
    pending = supervisor_pending_for_return(session, rid)

    refund = session.execute(select(Refund).where(Refund.return_id == rid).order_by(Refund.refund_id.desc()).limit(1)).scalar_one_or_none()
    replacement = session.execute(
        select(ReplacementRequest).where(ReplacementRequest.return_id == rid).order_by(ReplacementRequest.replacement_id.desc()).limit(1)
    ).scalar_one_or_none()
    notification = session.execute(
        select(CustomerNotification).where(CustomerNotification.return_id == rid).order_by(CustomerNotification.notification_id.desc()).limit(1)
    ).scalar_one_or_none()

    return {
        "return_id": rid,
        "return_status": row.return_status,
        "requested_resolution": row.requested_resolution,
        "received_date": handoff.get("received_date"),
        "inspection_count": insp_count,
        "warehouse_work_complete": verdict is not None,
        "warehouse_queue_stage": handoff.get("warehouse_queue_stage"),
        "next_warehouse_step": handoff.get("next_warehouse_step"),
        "analyst_case_open": handoff.get("analyst_case_open"),
        "active_case": handoff.get("active_case"),
        "latest_inspection": handoff.get("latest_inspection"),
        "warehouse_verdict": verdict,
        "analyst_workflow_stage": stage,
        "analyst_workflow_stage_label": STAGE_LABELS.get(stage or "") if stage else None,
        "analyst_next_action": analyst.get("analyst_next_action") if analyst else None,
        "next_owner": _OWNER.get(stage or ""),
        "supervisor_pending": pending,
        "refund": (
            {
                "refund_id": refund.refund_id,
                "amount_paise": refund.refund_amount,
                "status": refund.refund_status,
                "approval": refund.approval_status,
                "decision_reason": refund.decision_reason,
                "decided_by": refund.decided_by,
            }
            if refund
            else None
        ),
        "replacement": replacement_to_dict(replacement) if replacement else None,
        "notification": notification_to_dict(notification) if notification else None,
        "status_summary": _status_summary(
            stage=stage, return_status=row.return_status, requested_resolution=row.requested_resolution, verdict=verdict
        ),
    }


def build_agent_workflow_context_message(session: Session, return_id: str) -> str | None:
    """Inject live workflow JSON so every persona starts from the same DB truth."""
    snap = build_return_workflow_snapshot(session, return_id)
    if snap.get("error"):
        return None
    return (
        "LIVE WORKFLOW SNAPSHOT (single source of truth: your answer must match this for status/stage; "
        "call get_return_workflow_status again only if the user says they just clicked Approve/Reject "
        "or recorded inspection on the dashboard):\n" + json.dumps(snap, default=str)
    )
