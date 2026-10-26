"""Replacement request workflow (mirrors refunds: analyst submits, supervisor decides)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import ActorType, ReplacementStatus, SourceType
from app.models.tables import OrderItem, Product, ReplacementRequest, Return
from app.security.deps import CurrentUser
from app.services.audit import record_audit
from app.services.return_events import record_return_event
from app.services.return_status import on_replacement_decided


class ReplacementServiceError(Exception):
    def __init__(self, message: str, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code


_OPEN = (ReplacementStatus.REQUESTED.value,)


def replacement_to_dict(row: ReplacementRequest) -> dict:
    return {
        "replacement_id": row.replacement_id,
        "return_id": row.return_id,
        "product_id": row.product_id,
        "status": row.status,
        "replacement_order_id": row.replacement_order_id,
        "requested_by": row.requested_by,
        "decision_reason": row.decision_reason,
        "decided_by": row.decided_by,
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_replacements(session: Session, *, status: str | None = None, limit: int = 100) -> list[ReplacementRequest]:
    query = select(ReplacementRequest).order_by(ReplacementRequest.replacement_id.desc()).limit(limit)
    if status:
        query = query.where(ReplacementRequest.status == status)
    return list(session.execute(query).scalars().all())


def create_replacement_request(
    session: Session,
    *,
    return_id: str,
    actor: CurrentUser,
) -> ReplacementRequest:
    """Analyst submits a replacement. Needs a case and a feasible warehouse verdict; stock is re-checked."""
    from app.services.handoff import WorkflowError, assert_ready_for_submission, mark_case_submitted

    return_row = session.get(Return, return_id)
    if return_row is None:
        raise ReplacementServiceError("Return not found", "not_found")
    item = session.get(OrderItem, return_row.order_item_id)
    if item is None:
        raise ReplacementServiceError("Order item not found", "not_found")

    existing = session.execute(
        select(ReplacementRequest).where(ReplacementRequest.return_id == return_id, ReplacementRequest.status.in_(_OPEN))
    ).scalars().first()
    if existing is not None:
        raise ReplacementServiceError(f"Replacement {existing.replacement_id} is already open for this return.", "duplicate_open_request")

    try:
        case = assert_ready_for_submission(session, return_id, "replacement")
    except WorkflowError as exc:
        raise ReplacementServiceError(str(exc), exc.code) from exc

    product = session.get(Product, item.product_id)
    if product is None or product.stock_on_hand <= 0:
        raise ReplacementServiceError("The product is out of stock, so a replacement cannot be requested.", "no_stock")

    row = ReplacementRequest(
        return_id=return_id,
        product_id=item.product_id,
        status=ReplacementStatus.REQUESTED.value,
        replacement_order_id=None,
        created_at=utc_now(),
        requested_by=actor.username,
    )
    session.add(row)
    session.flush()
    record_return_event(
        session,
        return_id=return_id,
        event_type="other",
        description=f"Replacement {row.replacement_id} requested by {actor.username}; awaiting supervisor.",
        source_type=SourceType.SYSTEM.value,
        source_id=f"replacement:{row.replacement_id}:requested",
    )
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="create_replacement_request",
        target_entity="replacement_request",
        target_id=str(row.replacement_id),
        execution_result="succeeded",
        evidence_references={"return_id": return_id},
    )
    mark_case_submitted(session, case, actor)
    session.commit()
    session.refresh(row)
    return row


def decide_replacement(
    session: Session,
    *,
    replacement_id: int,
    actor: CurrentUser,
    approve: bool,
    reason: str | None = None,
) -> ReplacementRequest:
    """Supervisor decision. Approval reserves one unit of stock; both outcomes go back to the analyst."""
    from app.services.handoff import finish_case_after_decision
    from app.services.notifications import NotificationError, draft_notification

    row = session.get(ReplacementRequest, replacement_id)
    if row is None:
        raise ReplacementServiceError("Replacement request not found", "not_found")
    if row.status != ReplacementStatus.REQUESTED.value:
        raise ReplacementServiceError("Replacement is not pending approval.")
    reason = (reason or "").strip() or None
    if not approve and not reason:
        raise ReplacementServiceError("A reason is required when rejecting a replacement.", "reason_required")

    if approve:
        product = session.get(Product, row.product_id)
        if product is None or product.stock_on_hand <= 0:
            raise ReplacementServiceError("The product is out of stock, so the replacement cannot be approved.", "no_stock")
        product.stock_on_hand -= 1
        row.status = ReplacementStatus.APPROVED.value
        row.replacement_order_id = f"RPL-{row.replacement_id:05d}"
    else:
        row.status = ReplacementStatus.CANCELLED.value
    row.decision_reason = reason
    row.decided_by = actor.username
    row.decided_at = utc_now()

    on_replacement_decided(session, row.return_id, row.replacement_id, approve, actor)
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="decide_replacement",
        target_entity="replacement_request",
        target_id=str(row.replacement_id),
        execution_result="approved" if approve else "rejected",
        evidence_references={"reason": reason},
    )
    finish_case_after_decision(
        session,
        row.return_id,
        actor,
        notes=f"Replacement {row.replacement_id} {'approved' if approve else 'rejected'} by {actor.username}"
        + (f": {reason}" if reason else "."),
    )
    try:
        draft_notification(
            session,
            return_id=row.return_id,
            kind="replacement_approved" if approve else "replacement_rejected",
            actor=actor,
            reason=reason,
        )
    except NotificationError:
        pass
    session.commit()
    session.refresh(row)
    return row
