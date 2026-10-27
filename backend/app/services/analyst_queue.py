"""Returns analyst work queue (single-pool demo; future: filter by assigned_to)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import (
    ActionType,
    ApprovalStatus,
    RefundStatus,
    RequestedResolution,
    ReplacementStatus,
    ReturnStatus,
)
from app.models.tables import (
    ActionRequest,
    CustomerNotification,
    Inspection,
    InvestigationCase,
    Refund,
    ReplacementRequest,
    Return,
    WarehouseVerdict,
)
from app.services.case_transitions import ACTIVE_CASE_STATUSES
from app.services.cases import get_active_case

ACTIVE_CASE_VALUES = [c.value for c in ACTIVE_CASE_STATUSES]

_TERMINAL_RETURN = {
    ReturnStatus.RESOLVED.value,
    ReturnStatus.CLOSED.value,
    ReturnStatus.REJECTED.value,
}

_PRE_RECEIPT = {
    ReturnStatus.REQUESTED.value,
    ReturnStatus.APPROVED.value,
    ReturnStatus.PICKUP_SCHEDULED.value,
    ReturnStatus.IN_TRANSIT.value,
}

STAGE_LABELS: dict[str, str] = {
    "investigate": "Investigate return and open a case",
    "await_warehouse": "With warehouse (inspect and give verdict)",
    "submit_refund": "Warehouse approved: submit refund to supervisor",
    "submit_replacement": "Warehouse approved: submit replacement to supervisor",
    "decline_request": "Warehouse declined: decline request and review message",
    "await_supervisor": "Awaiting supervisor decision",
    "customer_follow_up": "Review and confirm customer message",
}

# Lower rank = needs the analyst sooner.
_STAGE_PRIORITY = {
    "customer_follow_up": 0,
    "decline_request": 1,
    "submit_refund": 2,
    "submit_replacement": 2,
    "investigate": 3,
    "await_warehouse": 4,
    "await_supervisor": 5,
}
ANALYST_TURN_STAGES = frozenset({"customer_follow_up", "decline_request", "submit_refund", "submit_replacement", "investigate"})
INVESTIGATE_SHOWN = 30  # newest un-triaged returns shown; all returns already in flight are always shown


def _refund_snapshot(session: Session, return_id: str) -> Refund | None:
    return session.execute(
        select(Refund).where(Refund.return_id == return_id).order_by(Refund.refund_id.desc()).limit(1)
    ).scalar_one_or_none()


def _replacement_snapshot(session: Session, return_id: str) -> ReplacementRequest | None:
    return session.execute(
        select(ReplacementRequest)
        .where(ReplacementRequest.return_id == return_id)
        .order_by(ReplacementRequest.replacement_id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _pending_supervisor_action(session: Session, return_id: str) -> ActionRequest | None:
    return session.execute(
        select(ActionRequest)
        .where(
            ActionRequest.return_id == return_id,
            ActionRequest.approval_status == ApprovalStatus.PENDING.value,
            ActionRequest.action_type.in_(
                (
                    ActionType.REQUEST_REFUND.value,
                    ActionType.CREATE_REPLACEMENT_REQUEST.value,
                )
            ),
        )
        .order_by(ActionRequest.action_id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _inspection_count(session: Session, return_id: str) -> int:
    return int(
        session.execute(
            select(func.count()).select_from(Inspection).where(Inspection.return_id == return_id)
        ).scalar_one()
    )


def _latest_verdict(session: Session, return_id: str) -> WarehouseVerdict | None:
    return session.execute(
        select(WarehouseVerdict).where(WarehouseVerdict.return_id == return_id).order_by(WarehouseVerdict.verdict_id.desc()).limit(1)
    ).scalar_one_or_none()


def _draft_notification(session: Session, return_id: str) -> CustomerNotification | None:
    return session.execute(
        select(CustomerNotification)
        .where(CustomerNotification.return_id == return_id, CustomerNotification.status == "draft")
        .order_by(CustomerNotification.notification_id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _classify_stage(
    row: Return,
    *,
    has_case: bool,
    inspection_count: int,
    refund: Refund | None,
    replacement: ReplacementRequest | None,
    pending_action: ActionRequest | None,
    verdict: WarehouseVerdict | None = None,
    draft: CustomerNotification | None = None,
) -> str:
    """Whose move is it? Derived only from database rows, so every persona sees the same truth."""
    if draft is not None:
        return "customer_follow_up"
    if pending_action is not None:
        return "await_supervisor"

    if refund is not None:
        if refund.refund_status == RefundStatus.COMPLETED.value or refund.refund_status == RefundStatus.CANCELLED.value:
            return "customer_follow_up" if row.return_status != ReturnStatus.CLOSED.value else "closed"
        if refund.approval_status in (ApprovalStatus.PENDING.value, ApprovalStatus.APPROVED.value):
            return "await_supervisor"
        if refund.approval_status == ApprovalStatus.REJECTED.value:
            return "customer_follow_up" if row.return_status != ReturnStatus.CLOSED.value else "closed"

    if replacement is not None:
        if replacement.status == ReplacementStatus.REQUESTED.value:
            return "await_supervisor"
        if replacement.status in (
            ReplacementStatus.APPROVED.value,
            ReplacementStatus.DISPATCHED.value,
            ReplacementStatus.COMPLETED.value,
            ReplacementStatus.CANCELLED.value,
        ):
            return "customer_follow_up" if row.return_status != ReturnStatus.CLOSED.value else "closed"

    if row.return_status in (ReturnStatus.CLOSED.value,):
        return "closed"
    if row.return_status == ReturnStatus.REJECTED.value:
        return "closed"
    if not has_case:
        return "investigate"
    if inspection_count == 0 or verdict is None:
        return "await_warehouse"
    if not verdict.feasible or verdict.recommendation != "proceed":
        return "decline_request"
    return "submit_replacement" if verdict.resolution_type == "replacement" else "submit_refund"


def _stage_rank(stage: str) -> int:
    return _STAGE_PRIORITY.get(stage, 99)


def _engaged_return_ids(session: Session) -> set[str]:
    """Returns already in flight: an active case, an open request, a pending approval, or an unsent customer message."""
    ids: set[str] = set()
    queries = [
        select(InvestigationCase.return_id).where(InvestigationCase.case_status.in_(ACTIVE_CASE_VALUES)),
        select(Refund.return_id).where(Refund.refund_status.in_([RefundStatus.REQUESTED.value, RefundStatus.APPROVED.value])),
        select(ReplacementRequest.return_id).where(ReplacementRequest.status == ReplacementStatus.REQUESTED.value),
        select(CustomerNotification.return_id).where(CustomerNotification.status == "draft"),
        select(ActionRequest.return_id).where(
            ActionRequest.approval_status == ApprovalStatus.PENDING.value, ActionRequest.return_id.is_not(None)
        ),
    ]
    for q in queries:
        ids.update(r for r in session.execute(q).scalars().all() if r)
    return ids


def build_analyst_work_queue(session: Session, *, limit: int = 300) -> list[dict[str, Any]]:
    """Everything in flight (always shown, never crowded out) plus the newest returns waiting for triage."""
    session.expire_all()
    engaged = _engaged_return_ids(session)
    rows = list(session.execute(select(Return).where(Return.return_id.in_(engaged))).scalars().all()) if engaged else []
    fresh = list(
        session.execute(
            select(Return)
            .where(Return.return_status.not_in(list(_TERMINAL_RETURN)), Return.return_id.not_in(engaged or {""}))
            .order_by(Return.request_date.desc())
            .limit(INVESTIGATE_SHOWN)
        ).scalars().all()
    )

    items: list[dict[str, Any]] = []
    for row in rows + fresh:
        active = get_active_case(session, row.return_id)
        insp_count = _inspection_count(session, row.return_id)
        refund = _refund_snapshot(session, row.return_id)
        replacement = _replacement_snapshot(session, row.return_id)
        verdict = _latest_verdict(session, row.return_id)
        draft = _draft_notification(session, row.return_id)
        stage = _classify_stage(
            row,
            has_case=active is not None,
            inspection_count=insp_count,
            refund=refund,
            replacement=replacement,
            pending_action=_pending_supervisor_action(session, row.return_id),
            verdict=verdict,
            draft=draft,
        )
        if stage == "closed":
            continue
        items.append(
            {
                "kind": "analyst_work_item",
                "return_id": row.return_id,
                "title": row.return_id,
                "subtitle": f"{row.return_reason.replace('_', ' ')} · {row.requested_resolution} · {row.return_status}",
                "status": row.return_status,
                "workflow_stage": stage,
                "next_action": STAGE_LABELS.get(stage, "Review"),
                "your_move": stage in ANALYST_TURN_STAGES,
                "requested_resolution": row.requested_resolution,
                "case_id": active.case_id if active else None,
                "priority": active.priority if active else None,
                "inspection_count": insp_count,
                "warehouse_verdict": verdict.recommendation if verdict else None,
                "warehouse_notes": verdict.notes if verdict else None,
                "notification_id": draft.notification_id if draft else None,
                "refund_id": refund.refund_id if refund else None,
                "refund_status": refund.refund_status if refund else None,
                "approval_status": refund.approval_status if refund else None,
            }
        )

    items.sort(key=lambda x: (_stage_rank(x["workflow_stage"]), x["return_id"]))
    return items[:limit]


def supervisor_pending_for_return(session: Session, return_id: str) -> dict[str, Any]:
    """Pending refund or replacement action awaiting supervisor (shared across UI and agent)."""
    pending_action = _pending_supervisor_action(session, return_id)
    refund = _refund_snapshot(session, return_id)
    if pending_action is not None:
        kind = (
            "replacement"
            if pending_action.action_type == ActionType.CREATE_REPLACEMENT_REQUEST.value
            else "refund"
        )
        return {
            "pending": True,
            "kind": kind,
            "action_id": pending_action.action_id,
            "refund_id": None,
            "amount_paise": None,
            "requested_by": pending_action.requested_by,
        }
    if refund is not None and (
        refund.approval_status == ApprovalStatus.PENDING.value
        or refund.refund_status == RefundStatus.REQUESTED.value
    ):
        return {
            "pending": True,
            "kind": "refund",
            "action_id": None,
            "refund_id": refund.refund_id,
            "amount_paise": refund.refund_amount,
            "requested_by": None,
        }
    replacement = _replacement_snapshot(session, return_id)
    if replacement is not None and replacement.status == ReplacementStatus.REQUESTED.value:
        return {
            "pending": True,
            "kind": "replacement",
            "action_id": None,
            "refund_id": None,
            "amount_paise": None,
            "requested_by": None,
        }
    return {
        "pending": False,
        "kind": None,
        "action_id": None,
        "refund_id": None,
        "amount_paise": None,
        "requested_by": None,
    }


def classify_return_workflow(session: Session, return_id: str) -> dict[str, Any] | None:
    row = session.get(Return, return_id)
    if row is None:
        return None
    active = get_active_case(session, return_id)
    insp_count = _inspection_count(session, return_id)
    verdict = _latest_verdict(session, return_id)
    draft = _draft_notification(session, return_id)
    stage = _classify_stage(
        row,
        has_case=active is not None,
        inspection_count=insp_count,
        refund=_refund_snapshot(session, return_id),
        replacement=_replacement_snapshot(session, return_id),
        pending_action=_pending_supervisor_action(session, return_id),
        verdict=verdict,
        draft=draft,
    )
    if stage == "closed":
        return None
    return {
        "analyst_workflow_stage": stage,
        "analyst_next_action": STAGE_LABELS.get(stage, "Review"),
        "case_id": active.case_id if active else None,
        "inspection_count": insp_count,
        "awaiting_warehouse": stage == "await_warehouse",
        "ready_to_submit": stage in ("submit_refund", "submit_replacement"),
        "notification_id": draft.notification_id if draft else None,
    }


def analyst_queue_kpis(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {k: 0 for k in STAGE_LABELS}
    for item in items:
        stage = item.get("workflow_stage", "")
        if stage in counts:
            counts[stage] += 1
    return {
        "queue_total": len(items),
        "your_move": sum(1 for i in items if i.get("your_move")),
        "needs_investigation": counts["investigate"],
        "awaiting_warehouse": counts["await_warehouse"],
        "ready_for_supervisor": counts["submit_refund"] + counts["submit_replacement"],
        "to_decline": counts["decline_request"],
        "pending_supervisor": counts["await_supervisor"],
        "customer_follow_up": counts["customer_follow_up"],
    }
