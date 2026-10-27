"""Returns supervisor approval queue (refund + replacement requests from analysts)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ActionType, ApprovalStatus, RefundStatus
from app.models.tables import ActionRequest, Refund, Return
from app.services.return_workflow import build_return_workflow_snapshot
from app.services.timeline import build_return_timeline

_SUPERVISOR_ACTION_TYPES = frozenset(
    {
        ActionType.REQUEST_REFUND.value,
        ActionType.CREATE_REPLACEMENT_REQUEST.value,
    }
)


def _action_label(action_type: str) -> str:
    if action_type == ActionType.CREATE_REPLACEMENT_REQUEST.value:
        return "replacement"
    if action_type == ActionType.REQUEST_REFUND.value:
        return "refund"
    return action_type.replace("_", " ")


def build_supervisor_approval_queue(session: Session, *, limit: int = 50) -> list[dict[str, Any]]:
    session.expire_all()
    items: list[dict[str, Any]] = []

    refunds = list(
        session.execute(
            select(Refund)
            .where(
                Refund.refund_status == RefundStatus.REQUESTED.value,
                Refund.approval_status == ApprovalStatus.PENDING.value,
            )
            .order_by(Refund.refund_id.desc())
            .limit(limit)
        ).scalars().all()
    )
    for refund in refunds:
        row = session.get(Return, refund.return_id)
        workflow = build_return_workflow_snapshot(session, refund.return_id)
        items.append(
            {
                "kind": "supervisor_approval_item",
                "approval_kind": "refund",
                "return_id": refund.return_id,
                "title": refund.return_id,
                "subtitle": (
                    f"Refund · ₹{refund.refund_amount / 100:,.2f} · "
                    f"{row.requested_resolution if row else '—'}"
                ),
                "refund_id": refund.refund_id,
                "action_id": None,
                "amount_paise": refund.refund_amount,
                "requested_by": None,
                "action_type": ActionType.REQUEST_REFUND.value,
                "workflow_stage": workflow.get("analyst_workflow_stage"),
                "inspection_count": workflow.get("inspection_count"),
                "status_summary": workflow.get("status_summary"),
            }
        )

    actions = list(
        session.execute(
            select(ActionRequest)
            .where(
                ActionRequest.approval_status == ApprovalStatus.PENDING.value,
                ActionRequest.action_type.in_(tuple(_SUPERVISOR_ACTION_TYPES)),
            )
            .order_by(ActionRequest.action_id.desc())
            .limit(limit)
        ).scalars().all()
    )
    seen_returns: set[str] = {i["return_id"] for i in items if i.get("return_id")}
    for action in actions:
        rid = action.return_id or ""
        if not rid:
            continue
        if action.action_type == ActionType.REQUEST_REFUND.value and rid in seen_returns:
            continue
        row = session.get(Return, rid)
        workflow = build_return_workflow_snapshot(session, rid)
        kind = _action_label(action.action_type)
        items.append(
            {
                "kind": "supervisor_approval_item",
                "approval_kind": kind,
                "return_id": rid,
                "title": rid,
                "subtitle": (
                    f"{kind.replace('_', ' ').title()} request · "
                    f"by {action.requested_by} · "
                    f"{row.requested_resolution if row else '—'}"
                ),
                "refund_id": None,
                "action_id": action.action_id,
                "amount_paise": None,
                "requested_by": action.requested_by,
                "action_type": action.action_type,
                "workflow_stage": workflow.get("analyst_workflow_stage"),
                "inspection_count": workflow.get("inspection_count"),
                "status_summary": workflow.get("status_summary"),
            }
        )
        seen_returns.add(rid)

    from app.models.enums import ReplacementStatus
    from app.models.tables import ReplacementRequest

    replacements = list(
        session.execute(
            select(ReplacementRequest)
            .where(ReplacementRequest.status == ReplacementStatus.REQUESTED.value)
            .order_by(ReplacementRequest.replacement_id.desc())
            .limit(limit)
        ).scalars().all()
    )
    for rep in replacements:
        row = session.get(Return, rep.return_id)
        workflow = build_return_workflow_snapshot(session, rep.return_id)
        items.append(
            {
                "kind": "supervisor_approval_item",
                "approval_kind": "replacement",
                "return_id": rep.return_id,
                "title": rep.return_id,
                "subtitle": f"Replacement · {row.return_reason.replace('_', ' ') if row else '-'} · by {rep.requested_by or 'analyst'}",
                "refund_id": None,
                "replacement_id": rep.replacement_id,
                "action_id": None,
                "amount_paise": None,
                "requested_by": rep.requested_by,
                "action_type": "create_replacement_request",
                "workflow_stage": workflow.get("analyst_workflow_stage"),
                "inspection_count": workflow.get("inspection_count"),
                "status_summary": workflow.get("status_summary"),
            }
        )

    for item in items:  # every item carries what the warehouse and analyst already established
        rid = item.get("return_id")
        if rid:
            snap = build_return_workflow_snapshot(session, rid)
            item["warehouse_verdict"] = snap.get("warehouse_verdict")
            item["latest_inspection"] = snap.get("latest_inspection")
            item["case"] = snap.get("active_case")
            item["workflow_timeline"] = build_return_timeline(session, rid)

    items.sort(key=lambda x: (x.get("return_id") or "", x.get("refund_id") or 0, x.get("replacement_id") or 0, x.get("action_id") or 0))
    return items[:limit]


def supervisor_queue_kpis(items: list[dict[str, Any]]) -> dict[str, int]:
    refunds = sum(1 for i in items if i.get("approval_kind") == "refund")
    replacements = sum(1 for i in items if i.get("approval_kind") == "replacement")
    return {
        "queue_total": len(items),
        "pending_refunds": refunds,
        "pending_replacements": replacements,
    }
