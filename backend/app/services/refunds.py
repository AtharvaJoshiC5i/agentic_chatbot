"""Refund request, approval, and execution."""

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import ApprovalStatus, RefundStatus, SourceType
from app.models.tables import OrderItem, Refund, Return
from app.security.deps import CurrentUser
from app.services.audit import record_audit
from app.services.refundable import calculate_refundable_amount_paise
from app.services.return_events import record_return_event
from app.services.return_status import on_refund_completed, on_refund_rejected
from app.models.enums import ActorType


class RefundServiceError(Exception):
    def __init__(self, message: str, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code


def list_refunds(
    session: Session,
    *,
    status: str | None = None,
    approval_status: str | None = None,
    return_id: str | None = None,
    limit: int = 100,
) -> list[Refund]:
    query = select(Refund).order_by(Refund.refund_id.desc())
    if status:
        query = query.where(Refund.refund_status == status.strip().lower())
    if approval_status:
        query = query.where(Refund.approval_status == approval_status.strip().lower())
    if return_id:
        query = query.where(Refund.return_id == return_id.strip().upper())
    return list(session.execute(query.limit(limit)).scalars().all())


def count_refunds_pending_approval(session: Session) -> int:
    return int(
        session.execute(
            select(func.count())
            .select_from(Refund)
            .where(
                Refund.refund_status == RefundStatus.REQUESTED.value,
                Refund.approval_status == ApprovalStatus.PENDING.value,
            )
        ).scalar_one()
    )


def get_refund_for_return(session: Session, return_id: str) -> Refund | None:
    return session.execute(
        select(Refund).where(Refund.return_id == return_id).order_by(Refund.refund_id.desc())
    ).scalars().first()


def request_refund(
    session: Session,
    *,
    return_id: str,
    refund_amount_paise: int,
    idempotency_key: str,
    actor: CurrentUser,
) -> Refund:
    if refund_amount_paise < 0:
        raise RefundServiceError("refund_amount must be non-negative")

    return_row = session.get(Return, return_id)
    if return_row is None:
        raise RefundServiceError("Return not found", "not_found")

    existing_key = session.execute(
        select(Refund).where(Refund.idempotency_key == idempotency_key)
    ).scalar_one_or_none()
    if existing_key is not None:
        return existing_key

    completed = session.execute(
        select(Refund).where(
            Refund.return_id == return_id,
            Refund.refund_status == RefundStatus.COMPLETED,
        )
    ).scalar_one_or_none()
    if completed is not None:
        raise RefundServiceError(
            "A completed refund already exists for this return.",
            "duplicate_refund",
        )

    open_request = session.execute(
        select(Refund).where(
            Refund.return_id == return_id,
            Refund.refund_status.in_([RefundStatus.REQUESTED.value, RefundStatus.APPROVED.value]),
        )
    ).scalars().first()
    if open_request is not None:
        raise RefundServiceError(
            f"Refund {open_request.refund_id} is already open for this return.",
            "duplicate_open_request",
        )

    from app.services.handoff import WorkflowError, assert_ready_for_submission, mark_case_submitted

    try:
        case = assert_ready_for_submission(session, return_id, "refund")
    except WorkflowError as exc:
        raise RefundServiceError(str(exc), exc.code) from exc

    amounts = calculate_refundable_amount_paise(session, return_id)
    if refund_amount_paise > amounts["remaining_refundable_paise"]:
        raise RefundServiceError(
            "refund_amount exceeds remaining refundable amount",
            "exceeds_remaining",
        )

    refund = Refund(
        return_id=return_id,
        refund_amount=refund_amount_paise,
        refund_status=RefundStatus.REQUESTED,
        approval_status=ApprovalStatus.PENDING,
        processed_date=None,
        idempotency_key=idempotency_key,
    )
    session.add(refund)
    session.flush()
    record_return_event(
        session,
        return_id=return_id,
        event_type="refund_requested",
        description=f"Refund {refund.refund_id} requested for {refund_amount_paise} paise.",
        source_type=SourceType.REFUND.value,
        source_id=f"{refund.refund_id}:requested",
    )
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="request_refund",
        target_entity="refund",
        target_id=str(refund.refund_id),
        execution_result="succeeded",
        evidence_references={"return_id": return_id, "amount_paise": refund_amount_paise},
    )
    mark_case_submitted(session, case, actor)  # case -> PENDING_APPROVAL: now visible in the supervisor queue
    session.commit()
    session.refresh(refund)
    return refund


def approve_refund(
    session: Session,
    refund_id: int,
    actor: CurrentUser,
    approve: bool = True,
    reason: str | None = None,
) -> Refund:
    """Supervisor decision. Approval pays the refund out immediately; both outcomes are handed back to the analyst."""
    from app.services.handoff import finish_case_after_decision
    from app.services.notifications import NotificationError, draft_notification

    refund = session.get(Refund, refund_id)
    if refund is None:
        raise RefundServiceError("Refund not found", "not_found")
    if refund.approval_status != ApprovalStatus.PENDING:
        raise RefundServiceError("Refund is not pending approval")
    reason = (reason or "").strip() or None
    if not approve and not reason:
        raise RefundServiceError("A reason is required when rejecting a refund.", "reason_required")

    refund.decision_reason = reason
    refund.decided_by = actor.username
    refund.decided_at = utc_now()

    if not approve:
        refund.approval_status = ApprovalStatus.REJECTED
        refund.refund_status = RefundStatus.CANCELLED
        on_refund_rejected(session, refund.return_id, refund.refund_id, actor)
        record_audit(
            session,
            actor=actor,
            actor_type=ActorType.USER,
            action_type="approve_refund",
            target_entity="refund",
            target_id=str(refund.refund_id),
            execution_result="rejected",
            evidence_references={"reason": reason},
        )
        finish_case_after_decision(
            session, refund.return_id, actor, notes=f"Refund {refund.refund_id} rejected by {actor.username}: {reason}"
        )
        try:
            draft_notification(session, return_id=refund.return_id, kind="refund_rejected", actor=actor, reason=reason)
        except NotificationError:
            pass
        session.commit()
        session.refresh(refund)
        return refund

    refund.approval_status = ApprovalStatus.APPROVED
    refund.refund_status = RefundStatus.APPROVED
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="approve_refund",
        target_entity="refund",
        target_id=str(refund.refund_id),
        execution_result="approved",
    )
    session.commit()
    refund = execute_refund(session, refund_id, actor)  # pays out, resolves the return
    finish_case_after_decision(
        session, refund.return_id, actor, notes=f"Refund {refund.refund_id} approved and paid by {actor.username}."
    )
    try:
        draft_notification(
            session, return_id=refund.return_id, kind="refund_approved", actor=actor, amount_paise=refund.refund_amount
        )
    except NotificationError:
        pass
    session.commit()
    session.refresh(refund)
    return refund


def execute_refund(session: Session, refund_id: int, actor: CurrentUser) -> Refund:
    refund = session.get(Refund, refund_id)
    if refund is None:
        raise RefundServiceError("Refund not found", "not_found")

    if refund.refund_status == RefundStatus.COMPLETED:
        raise RefundServiceError("Refund already executed", "duplicate_refund")

    if refund.approval_status != ApprovalStatus.APPROVED:
        raise RefundServiceError("Refund must be approved before execution")

    amounts = calculate_refundable_amount_paise(
        session, refund.return_id, exclude_refund_id=refund.refund_id
    )
    if refund.refund_amount > amounts["remaining_refundable_paise"]:
        raise RefundServiceError(
            "Refund amount exceeds remaining refundable balance at execution time.",
            "exceeds_remaining",
        )

    other_completed = session.execute(
        select(Refund).where(
            Refund.return_id == refund.return_id,
            Refund.refund_status == RefundStatus.COMPLETED,
            Refund.refund_id != refund.refund_id,
        )
    ).scalar_one_or_none()
    if other_completed is not None:
        raise RefundServiceError(
            "Another completed refund exists for this return.",
            "duplicate_refund",
        )

    refund.refund_status = RefundStatus.COMPLETED
    refund.processed_date = utc_now()
    record_return_event(
        session,
        return_id=refund.return_id,
        event_type="refund_processed",
        description=f"Refund {refund.refund_id} completed ({refund.refund_amount} paise).",
        source_type=SourceType.REFUND.value,
        source_id=f"{refund.refund_id}:processed",
        event_timestamp=refund.processed_date,
    )
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="execute_refund",
        target_entity="refund",
        target_id=str(refund.refund_id),
        execution_result="succeeded",
        evidence_references={"return_id": refund.return_id},
    )
    on_refund_completed(session, refund.return_id, refund.refund_id, actor)
    session.commit()
    session.refresh(refund)
    return refund
