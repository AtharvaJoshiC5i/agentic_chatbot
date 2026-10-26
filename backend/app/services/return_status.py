"""Central return_status transitions (single state machine)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import ActorType, RefundStatus, ReturnStatus, SourceType
from app.models.tables import Refund, Return
from app.security.deps import CurrentUser
from app.services.audit import record_audit
from app.services.return_events import record_return_event

# Amount above this (paise) needs finance / second supervisor sign-off before payout.
REFUND_AUTO_PAYOUT_MAX_PAISE = 5_000_000  # ₹50,000


class ReturnStatusError(Exception):
    def __init__(self, message: str, code: str = "invalid_transition") -> None:
        super().__init__(message)
        self.code = code


_CASE_OPEN_FROM = frozenset(
    {ReturnStatus.RECEIVED.value, ReturnStatus.INSPECTING.value}
)
_PRE_RECEIPT_STATUSES = frozenset(
    {
        ReturnStatus.REQUESTED.value,
        ReturnStatus.APPROVED.value,
        ReturnStatus.PICKUP_SCHEDULED.value,
        ReturnStatus.IN_TRANSIT.value,
    }
)
_CASE_CREATE_ALLOWED = _CASE_OPEN_FROM | _PRE_RECEIPT_STATUSES | {ReturnStatus.INVESTIGATING.value}
_RECEIVE_FROM = _PRE_RECEIPT_STATUSES
_INVESTIGATING_FROM = frozenset(
    {
        ReturnStatus.RECEIVED.value,
        ReturnStatus.INSPECTING.value,
        ReturnStatus.INVESTIGATING.value,
    }
)
_RESOLVED_FROM = frozenset(
    {
        ReturnStatus.RECEIVED.value,
        ReturnStatus.INSPECTING.value,
        ReturnStatus.INVESTIGATING.value,
    }
)
_CLOSED_FROM = frozenset({ReturnStatus.RESOLVED.value, ReturnStatus.REJECTED.value})


def _set_status(
    session: Session,
    return_row: Return,
    new_status: str,
    *,
    actor: CurrentUser,
    description: str,
    event_type: str,
    source_id: str,
) -> None:
    old = return_row.return_status
    if old == new_status:
        return
    return_row.return_status = new_status
    record_return_event(
        session,
        return_id=return_row.return_id,
        event_type=event_type,
        description=description,
        source_type=SourceType.SYSTEM.value,
        source_id=source_id,
        event_timestamp=utc_now(),
    )
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="update_return_status",
        target_entity="return",
        target_id=return_row.return_id,
        execution_result="succeeded",
        evidence_references={"from": old, "to": new_status},
    )


def on_case_created(session: Session, return_id: str, case_id: int, actor: CurrentUser) -> None:
    row = session.get(Return, return_id)
    if row is None:
        return
    if row.return_status not in _CASE_CREATE_ALLOWED:
        raise ReturnStatusError(
            f"Cannot open investigation case from status {row.return_status}",
            "invalid_transition",
        )
    if row.return_status == ReturnStatus.INVESTIGATING.value:
        return
    if row.return_status in _PRE_RECEIPT_STATUSES:
        record_return_event(
            session,
            return_id=return_id,
            event_type="other",
            description=(
                f"Investigation case {case_id} opened; return handed to warehouse "
                f"(status remains {row.return_status} until receipt)."
            ),
            source_type=SourceType.SYSTEM.value,
            source_id=f"case:{case_id}:warehouse_handoff",
            event_timestamp=utc_now(),
        )
        return
    if row.return_status in _CASE_OPEN_FROM:
        _set_status(
            session,
            row,
            ReturnStatus.INVESTIGATING.value,
            actor=actor,
            description=f"Return moved to investigating (case {case_id}).",
            event_type="other",
            source_id=f"case:{case_id}:investigating",
        )


def receive_return_at_warehouse(
    session: Session,
    return_id: str,
    actor: CurrentUser,
) -> Return:
    """Mark return as received at warehouse (required before inspection)."""
    row = session.get(Return, return_id)
    if row is None:
        raise ReturnStatusError("Return not found", "not_found")
    if row.received_date is not None and row.return_status not in _PRE_RECEIPT_STATUSES:
        return row
    if row.return_status not in _RECEIVE_FROM:
        if row.return_status in (
            ReturnStatus.RECEIVED.value,
            ReturnStatus.INSPECTING.value,
            ReturnStatus.INVESTIGATING.value,
        ):
            if row.received_date is None:
                row.received_date = utc_now()
                session.flush()
            return row
        raise ReturnStatusError(
            f"Cannot receive return from status {row.return_status}",
            "invalid_transition",
        )
    now = utc_now()
    row.received_date = now
    _set_status(
        session,
        row,
        ReturnStatus.RECEIVED.value,
        actor=actor,
        description="Return received at warehouse.",
        event_type="warehouse_received",
        source_id=f"return:{return_id}:received",
    )
    session.commit()
    from app.services.handoff import claim_case_for_warehouse

    claim_case_for_warehouse(session, return_id, actor)
    session.refresh(row)
    return row


def on_inspection_recorded(session: Session, return_id: str, inspection_id: int, actor: CurrentUser) -> None:
    from app.services.cases import get_active_case

    row = session.get(Return, return_id)
    if row is None:
        return
    if row.return_status not in (
        ReturnStatus.RECEIVED.value,
        ReturnStatus.INSPECTING.value,
    ):
        return
    has_analyst_case = get_active_case(session, return_id) is not None
    if has_analyst_case:
        target = ReturnStatus.INVESTIGATING.value
        description = (
            f"Warehouse inspection {inspection_id} complete; return with returns analyst."
        )
    else:
        target = ReturnStatus.INSPECTING.value
        description = f"Return moved to inspecting (inspection {inspection_id})."
    _set_status(
        session,
        row,
        target,
        actor=actor,
        description=description,
        event_type="other",
        source_id=f"inspection:{inspection_id}",
    )


def on_refund_completed(session: Session, return_id: str, refund_id: int, actor: CurrentUser) -> None:
    row = session.get(Return, return_id)
    if row is None:
        return
    if row.return_status not in _RESOLVED_FROM:
        return
    _set_status(
        session,
        row,
        ReturnStatus.RESOLVED.value,
        actor=actor,
        description=f"Return resolved after refund {refund_id} completed.",
        event_type="other",
        source_id=f"refund:{refund_id}:resolved",
    )


def on_refund_rejected(session: Session, return_id: str, refund_id: int, actor: CurrentUser) -> None:
    row = session.get(Return, return_id)
    if row is None:
        return
    _set_status(
        session,
        row,
        ReturnStatus.REJECTED.value,
        actor=actor,
        description=f"Return rejected after refund {refund_id} was declined.",
        event_type="other",
        source_id=f"refund:{refund_id}:rejected",
    )


def on_case_resolved(session: Session, return_id: str, case_id: int, actor: CurrentUser) -> None:
    row = session.get(Return, return_id)
    if row is None:
        return
    completed = session.execute(
        select(Refund).where(
            Refund.return_id == return_id,
            Refund.refund_status == RefundStatus.COMPLETED.value,
        )
    ).first()
    if completed is not None:
        target = ReturnStatus.RESOLVED.value
    elif row.return_status == ReturnStatus.INVESTIGATING.value:
        target = ReturnStatus.RECEIVED.value
    else:
        return
    _set_status(
        session,
        row,
        target,
        actor=actor,
        description=f"Return status updated after case {case_id} resolved.",
        event_type="other",
        source_id=f"case:{case_id}:resolved",
    )


_DECLINE_FROM = frozenset(
    {
        ReturnStatus.RECEIVED.value,
        ReturnStatus.INSPECTING.value,
        ReturnStatus.INVESTIGATING.value,
    }
)


def on_declined(session: Session, return_id: str, reason: str, actor: CurrentUser) -> None:
    """Analyst declined the customer's request (refund or replacement) after the warehouse verdict."""
    row = session.get(Return, return_id)
    if row is None:
        return
    if row.return_status not in _DECLINE_FROM:
        raise ReturnStatusError(f"Cannot decline a return in status {row.return_status}", "invalid_transition")
    _set_status(
        session,
        row,
        ReturnStatus.REJECTED.value,
        actor=actor,
        description=f"Request declined by {actor.username}: {reason}",
        event_type="other",
        source_id=f"return:{return_id}:declined",
    )


def on_replacement_decided(session: Session, return_id: str, replacement_id: int, approved: bool, actor: CurrentUser) -> None:
    row = session.get(Return, return_id)
    if row is None or row.return_status not in _DECLINE_FROM:
        return
    _set_status(
        session,
        row,
        ReturnStatus.RESOLVED.value if approved else ReturnStatus.REJECTED.value,
        actor=actor,
        description=(
            f"Replacement {replacement_id} approved; return resolved."
            if approved
            else f"Replacement {replacement_id} was declined by the supervisor."
        ),
        event_type="other",
        source_id=f"replacement:{replacement_id}:{'approved' if approved else 'rejected'}",
    )


def close_return(
    session: Session,
    return_id: str,
    actor: CurrentUser,
    *,
    description: str = "Return closed by supervisor.",
) -> Return:
    row = session.get(Return, return_id)
    if row is None:
        raise ReturnStatusError("Return not found", "not_found")
    if row.return_status not in _CLOSED_FROM:
        raise ReturnStatusError(
            f"Return cannot be closed from status {row.return_status}",
            "invalid_transition",
        )
    _set_status(
        session,
        row,
        ReturnStatus.CLOSED.value,
        actor=actor,
        description=description,
        event_type="other",
        source_id=f"return:{return_id}:closed",
    )
    session.commit()
    session.refresh(row)
    return row
