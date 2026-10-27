"""Persona handoff workflow: analyst -> warehouse verdict -> analyst submission -> supervisor decision.

Every step writes its result to the database, so the next persona reads it from the same tables:
  analyst opens a case        -> case OPEN, return `investigating`, appears in the warehouse queue
  warehouse inspects          -> case IN_PROGRESS, assigned to the warehouse user
  warehouse gives a verdict   -> case READY_FOR_REVIEW, appears in the analyst queue
  analyst submits / declines  -> case PENDING_APPROVAL (or RESOLVED on decline), supervisor queue / notification draft
  supervisor decides          -> case RESOLVED, notification draft for the analyst
  analyst sends notification  -> case CLOSED, return `closed`
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import ActorType, CaseStatus, InspectionResult, RequestedResolution, SourceType
from app.investigation.investigation import run_investigation
from app.models.tables import (
    InvestigationCase,
    Inspection,
    OrderItem,
    Product,
    Return,
    WarehouseVerdict,
)
from app.security.deps import CurrentUser
from app.services.audit import record_audit
from app.services.case_transitions import can_transition
from app.services.cases import CaseServiceError, get_active_case, record_policy_rejection_case, transition_case_status
from app.services.return_events import record_return_event
from app.services.return_status import on_declined, on_policy_declined


_RANK = {
    CaseStatus.OPEN: 0,
    CaseStatus.ASSIGNED: 1,
    CaseStatus.IN_PROGRESS: 2,
    CaseStatus.AWAITING_EVIDENCE: 2,
    CaseStatus.READY_FOR_REVIEW: 3,
    CaseStatus.PENDING_APPROVAL: 4,
    CaseStatus.RESOLVED: 5,
    CaseStatus.CLOSED: 6,
}


class WorkflowError(Exception):
    """A workflow rule was not met (mapped to HTTP 409 by the routes)."""

    def __init__(self, message: str, code: str = "workflow_blocked") -> None:
        super().__init__(message)
        self.code = code


def required_resolution_type(return_row: Return) -> str:
    """The path the warehouse assesses: replacement requests are replacements, everything else is a refund."""
    if (return_row.requested_resolution or "").lower() == RequestedResolution.REPLACEMENT.value:
        return "replacement"
    return "refund"


def product_for_return(session: Session, return_row: Return) -> Product | None:
    item = session.get(OrderItem, return_row.order_item_id)
    return session.get(Product, item.product_id) if item else None


def inspection_count(session: Session, return_id: str) -> int:
    return int(session.execute(select(func.count()).select_from(Inspection).where(Inspection.return_id == return_id)).scalar_one())


def get_latest_verdict(session: Session, return_id: str) -> WarehouseVerdict | None:
    return session.execute(
        select(WarehouseVerdict).where(WarehouseVerdict.return_id == return_id).order_by(WarehouseVerdict.verdict_id.desc()).limit(1)
    ).scalar_one_or_none()


def verdict_to_dict(v: WarehouseVerdict | None) -> dict | None:
    if v is None:
        return None
    return {
        "verdict_id": v.verdict_id,
        "return_id": v.return_id,
        "resolution_type": v.resolution_type,
        "feasible": v.feasible,
        "stock_available": v.stock_available,
        "recommendation": v.recommendation,
        "notes": v.notes,
        "decided_by": v.decided_by,
        "decided_at": v.decided_at.isoformat() if v.decided_at else None,
    }


# --------------------------------------------------------------------------- case helpers


def advance_case(session: Session, case: InvestigationCase, path: list[CaseStatus], actor: CurrentUser, notes: str | None = None) -> None:
    """Move a case along `path`, skipping steps already passed and any step that is not allowed."""
    for target in path:
        current = CaseStatus(case.case_status)
        if _RANK[target] <= _RANK[current] or not can_transition(current, target):
            continue  # never move a case backwards or repeat a step
        transition_case_status(
            session,
            case_id=case.case_id,
            new_status=target,
            actor=actor,
            resolution_notes=notes if target in (CaseStatus.RESOLVED, CaseStatus.CLOSED) else None,
        )
        session.refresh(case)


def claim_case_for_warehouse(session: Session, return_id: str, actor: CurrentUser) -> None:
    """First warehouse action on a case: assign it to that user and mark it in progress."""
    case = get_active_case(session, return_id)
    if case is None or case.case_status not in {CaseStatus.OPEN.value, CaseStatus.ASSIGNED.value}:
        return
    case.assigned_to = actor.username
    advance_case(session, case, [CaseStatus.IN_PROGRESS], actor)
    record_return_event(
        session,
        return_id=return_id,
        event_type="case_updated",
        description=f"Case {case.case_id} picked up by warehouse ({actor.username}).",
        source_type=SourceType.CASE.value,
        source_id=f"{case.case_id}:warehouse_claimed",
    )
    session.commit()


# --------------------------------------------------------------------------- warehouse verdict


def record_verdict(
    session: Session,
    *,
    return_id: str,
    actor: CurrentUser,
    feasible: bool,
    recommendation: str,
    notes: str | None,
) -> WarehouseVerdict:
    row = session.get(Return, return_id)
    if row is None:
        raise WorkflowError("Return not found", "not_found")
    case = get_active_case(session, return_id)
    if case is None:
        raise WorkflowError("No active investigation case: the returns analyst must open one first.", "no_case")
    if case.case_status in (CaseStatus.PENDING_APPROVAL.value,):
        raise WorkflowError("The analyst has already submitted this case to the supervisor.", "already_submitted")
    if inspection_count(session, return_id) == 0:
        raise WorkflowError("Record the warehouse inspection before giving a verdict.", "inspection_required")
    latest_inspection = session.execute(
        select(Inspection)
        .where(Inspection.return_id == return_id)
        .order_by(Inspection.inspection_id.desc())
        .limit(1)
    ).scalar_one()
    if feasible and latest_inspection.inspection_result != InspectionResult.PASS.value:
        raise WorkflowError(
            "A request cannot be marked feasible unless the latest inspection passed. Record the inspection outcome first.",
            "inspection_unsuccessful",
        )

    recommendation = (recommendation or "").strip().lower()
    if recommendation not in ("proceed", "decline"):
        raise WorkflowError("recommendation must be 'proceed' or 'decline'.", "invalid_recommendation")
    if feasible and recommendation == "decline":
        raise WorkflowError("A feasible request cannot carry a 'decline' recommendation.", "inconsistent_verdict")
    if not feasible and recommendation == "proceed":
        raise WorkflowError("An infeasible request cannot carry a 'proceed' recommendation.", "inconsistent_verdict")
    if recommendation == "decline" and not (notes or "").strip():
        raise WorkflowError("Give the reason the request cannot be performed.", "reason_required")

    resolution_type = required_resolution_type(row)
    stock_available: bool | None = None
    if resolution_type == "replacement":
        product = product_for_return(session, row)
        stock_available = bool(product and product.stock_on_hand > 0)
        if feasible and not stock_available:
            raise WorkflowError("Replacement cannot be marked feasible: the product is out of stock.", "no_stock")

    verdict = WarehouseVerdict(
        return_id=return_id,
        case_id=case.case_id,
        resolution_type=resolution_type,
        feasible=feasible,
        stock_available=stock_available,
        recommendation=recommendation,
        notes=(notes or "").strip() or None,
        decided_by=actor.username,
        decided_at=utc_now(),
    )
    session.add(verdict)
    session.flush()
    if case.assigned_to is None:
        case.assigned_to = actor.username
    advance_case(session, case, [CaseStatus.IN_PROGRESS, CaseStatus.READY_FOR_REVIEW], actor)
    record_return_event(
        session,
        return_id=return_id,
        event_type="other",
        description=(
            f"Warehouse verdict: {resolution_type} {'feasible' if feasible else 'not feasible'} "
            f"({recommendation}). Returned to returns analyst."
        ),
        source_type=SourceType.CASE.value,
        source_id=f"verdict:{verdict.verdict_id}",
    )
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="record_warehouse_verdict",
        target_entity="warehouse_verdict",
        target_id=str(verdict.verdict_id),
        execution_result="succeeded",
        evidence_references={"return_id": return_id, "resolution_type": resolution_type, "recommendation": recommendation},
    )
    session.commit()
    session.refresh(verdict)
    return verdict


# --------------------------------------------------------------------------- analyst gate


def assert_ready_for_submission(session: Session, return_id: str, kind: str) -> InvestigationCase:
    """The analyst may submit a refund/replacement only when the warehouse verdict supports it."""
    if session.get(Return, return_id) is None:
        raise WorkflowError("Return not found", "not_found")
    case = get_active_case(session, return_id)
    if case is None:
        raise WorkflowError("Open an investigation case before submitting: the warehouse must assess it first.", "no_case")
    verdict = get_latest_verdict(session, return_id)
    if verdict is None:
        raise WorkflowError("Waiting for the warehouse verdict. Nothing can be submitted to the supervisor yet.", "verdict_required")
    if verdict.resolution_type != kind:
        raise WorkflowError(
            f"The warehouse assessed this return as a {verdict.resolution_type}; a {kind} cannot be submitted.",
            "resolution_mismatch",
        )
    if not verdict.feasible or verdict.recommendation != "proceed":
        raise WorkflowError(
            f"The warehouse says this {kind} cannot be performed ({verdict.notes or 'no reason given'}). "
            "Decline the request and notify the customer instead.",
            "warehouse_declined",
        )
    if case.case_status == CaseStatus.PENDING_APPROVAL.value:
        raise WorkflowError("This case is already with the supervisor.", "already_submitted")
    return case


def mark_case_submitted(session: Session, case: InvestigationCase, actor: CurrentUser) -> None:
    advance_case(session, case, [CaseStatus.IN_PROGRESS, CaseStatus.READY_FOR_REVIEW, CaseStatus.PENDING_APPROVAL], actor)


# --------------------------------------------------------------------------- analyst decline


def decline_return(session: Session, *, return_id: str, actor: CurrentUser, reason: str) -> Return:
    """Reject an out-of-policy request before handoff or a warehouse-declined request after inspection."""
    from app.services.notifications import draft_notification

    reason = (reason or "").strip()
    if not reason:
        raise WorkflowError("A reason is required to decline a request.", "reason_required")
    row = session.get(Return, return_id)
    if row is None:
        raise WorkflowError("Return not found", "not_found")
    case = get_active_case(session, return_id)
    if case is None:
        investigation = run_investigation(session, return_id)
        policy = investigation.f3_policy if investigation else None
        if policy is None or policy.within_return_window is not False:
            raise WorkflowError(
                "An early policy rejection requires a definite out-of-window result from the policy check. "
                "If eligible or uncertain, open the inspection case or gather the missing information.",
                "policy_not_failed",
            )
        basis = (
            f"Policy check: {policy.product_category} allows {policy.return_window_days} days; "
            f"this request was made {policy.days_after_delivery} days after delivery."
        )
        reason = f"{reason} {basis}"
        record_policy_rejection_case(session, return_id=return_id, reason=reason, actor=actor)
        on_policy_declined(session, return_id, reason, actor)
        draft_notification(session, return_id=return_id, kind="declined", actor=actor, reason=reason)
        record_audit(
            session,
            actor=actor,
            actor_type=ActorType.USER,
            action_type="decline_return_for_policy",
            target_entity="return",
            target_id=return_id,
            execution_result="succeeded",
            evidence_references={
                "reason": reason,
                "policy": {
                    "product_category": policy.product_category,
                    "return_window_days": policy.return_window_days,
                    "days_after_delivery": policy.days_after_delivery,
                    "delivery_date": policy.delivery_date.isoformat() if policy.delivery_date else None,
                    "return_request_date": policy.return_request_date.isoformat() if policy.return_request_date else None,
                    "within_return_window": policy.within_return_window,
                },
            },
        )
        session.commit()
        session.refresh(row)
        return row
    if get_latest_verdict(session, return_id) is None:
        raise WorkflowError("Wait for the warehouse verdict before declining.", "verdict_required")
    if case.case_status == CaseStatus.PENDING_APPROVAL.value:
        raise WorkflowError("This case is already with the supervisor.", "already_submitted")

    on_declined(session, return_id, reason, actor)
    advance_case(
        session, case, [CaseStatus.IN_PROGRESS, CaseStatus.READY_FOR_REVIEW, CaseStatus.RESOLVED], actor,
        notes=f"Declined by {actor.username}: {reason}",
    )
    draft_notification(session, return_id=return_id, kind="declined", actor=actor, reason=reason)
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="decline_return",
        target_entity="return",
        target_id=return_id,
        execution_result="succeeded",
        evidence_references={"reason": reason},
    )
    session.commit()
    session.refresh(row)
    return row


def finish_case_after_decision(session: Session, return_id: str, actor: CurrentUser, notes: str) -> None:
    """Supervisor decided: the case is resolved and the analyst is left with the customer follow-up."""
    case = get_active_case(session, return_id)
    if case is None:
        return
    advance_case(
        session, case,
        [CaseStatus.IN_PROGRESS, CaseStatus.READY_FOR_REVIEW, CaseStatus.PENDING_APPROVAL, CaseStatus.RESOLVED],
        actor, notes=notes,
    )


__all__ = [
    "CaseServiceError",
    "WorkflowError",
    "advance_case",
    "assert_ready_for_submission",
    "claim_case_for_warehouse",
    "decline_return",
    "finish_case_after_decision",
    "get_latest_verdict",
    "mark_case_submitted",
    "record_verdict",
    "required_resolution_type",
    "verdict_to_dict",
]
