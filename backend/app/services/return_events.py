"""Persist and sync return journey events (return_events table)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import DocumentType, RefundStatus, SourceType
from app.models.tables import (
    Delivery,
    DocumentMetadata,
    Inspection,
    InvestigationCase,
    Order,
    OrderItem,
    RecoveryTask,
    Refund,
    Return,
    ReturnEvent,
)


@dataclass(frozen=True)
class EventDraft:
    event_type: str
    event_timestamp: object
    description: str
    source_type: str
    source_id: str


def record_return_event(
    session: Session,
    *,
    return_id: str,
    event_type: str,
    description: str,
    source_type: str,
    source_id: str,
    event_timestamp: object | None = None,
    commit: bool = False,
) -> ReturnEvent:
    """Idempotent insert keyed by (return_id, event_type, source_type, source_id)."""
    ts = event_timestamp or utc_now()
    existing = session.execute(
        select(ReturnEvent).where(
            ReturnEvent.return_id == return_id,
            ReturnEvent.event_type == event_type,
            ReturnEvent.source_type == source_type,
            ReturnEvent.source_id == source_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    row = ReturnEvent(
        return_id=return_id,
        event_type=event_type,
        event_timestamp=ts,
        description=description,
        source_type=source_type,
        source_id=source_id,
    )
    session.add(row)
    session.flush()
    if commit:
        session.commit()
        session.refresh(row)
    return row


def _drafts_from_structured_data(session: Session, return_id: str) -> list[EventDraft]:
    return_row = session.get(Return, return_id)
    if return_row is None:
        return []

    drafts: list[EventDraft] = []

    def add(
        event_type: str,
        timestamp,
        description: str,
        source_type: str,
        source_id: str,
    ) -> None:
        if timestamp is None:
            return
        drafts.append(
            EventDraft(
                event_type=event_type,
                event_timestamp=timestamp,
                description=description,
                source_type=source_type,
                source_id=source_id,
            )
        )

    item = session.get(OrderItem, return_row.order_item_id)
    if item:
        order = session.get(Order, item.order_id)
        if order:
            add(
                "order_placed",
                order.order_date,
                f"Order {order.order_id} placed.",
                SourceType.ORDER.value,
                order.order_id,
            )
            delivery = session.execute(
                select(Delivery).where(Delivery.order_id == order.order_id)
            ).scalar_one_or_none()
            if delivery:
                add(
                    "dispatched",
                    delivery.dispatch_date,
                    f"Order dispatched (delivery {delivery.delivery_id}).",
                    SourceType.DELIVERY.value,
                    delivery.delivery_id,
                )
                add(
                    "delivered",
                    delivery.delivery_date,
                    f"Order delivered ({delivery.delivery_status}).",
                    SourceType.DELIVERY.value,
                    f"{delivery.delivery_id}:delivered",
                )
                if delivery.delivery_issue:
                    add(
                        "other",
                        delivery.delivery_date,
                        f"Delivery issue noted: {delivery.delivery_issue[:200]}",
                        SourceType.DELIVERY.value,
                        f"{delivery.delivery_id}:issue",
                    )

    add(
        "return_requested",
        return_row.request_date,
        f"Return requested ({return_row.return_reason}).",
        SourceType.RETURN.value,
        f"{return_row.return_id}:requested",
    )

    if return_row.received_date:
        add(
            "warehouse_received",
            return_row.received_date,
            f"Return received (status {return_row.return_status}).",
            SourceType.RETURN.value,
            f"{return_row.return_id}:received",
        )

    for doc in session.execute(
        select(DocumentMetadata).where(
            DocumentMetadata.return_id == return_id,
            DocumentMetadata.document_type == DocumentType.CUSTOMER_COMPLAINT.value,
        )
    ).scalars():
        add(
            "complaint_filed",
            doc.created_at,
            f"Customer complaint recorded ({doc.filename}).",
            SourceType.COMPLAINT.value,
            str(doc.document_id),
        )

    for inspection in session.execute(
        select(Inspection).where(Inspection.return_id == return_id)
    ).scalars():
        add(
            "inspection_completed",
            inspection.inspection_date,
            f"Inspection {inspection.inspection_id}: {inspection.inspection_result}.",
            SourceType.INSPECTION.value,
            str(inspection.inspection_id),
        )

    for case in session.execute(
        select(InvestigationCase).where(InvestigationCase.return_id == return_id)
    ).scalars():
        add(
            "investigation_opened",
            case.created_at,
            f"Case {case.case_id} opened ({case.issue_type}, {case.priority}).",
            SourceType.CASE.value,
            f"{case.case_id}:opened",
        )
        if case.assigned_to:
            add(
                "case_updated",
                case.created_at,
                f"Case {case.case_id} assigned to {case.assigned_to} ({case.case_status}).",
                SourceType.CASE.value,
                f"{case.case_id}:assigned",
            )

    for refund in session.execute(select(Refund).where(Refund.return_id == return_id)).scalars():
        if refund.refund_status == RefundStatus.COMPLETED.value and refund.processed_date:
            requested_at = refund.processed_date - timedelta(days=2)
            add(
                "refund_requested",
                requested_at,
                f"Refund {refund.refund_id} requested for {refund.refund_amount} paise.",
                SourceType.REFUND.value,
                f"{refund.refund_id}:requested",
            )
            add(
                "refund_processed",
                refund.processed_date,
                f"Refund {refund.refund_id} completed ({refund.refund_amount} paise).",
                SourceType.REFUND.value,
                f"{refund.refund_id}:processed",
            )
        else:
            add(
                "refund_requested",
                return_row.request_date,
                f"Refund {refund.refund_id} status {refund.refund_status}.",
                SourceType.REFUND.value,
                str(refund.refund_id),
            )

    for task in session.execute(
        select(RecoveryTask).where(RecoveryTask.return_id == return_id)
    ).scalars():
        add(
            "recovery_task_created",
            task.created_at,
            f"Recovery task {task.recovery_task_id} ({task.recovery_method}).",
            SourceType.RECOVERY_TASK.value,
            str(task.recovery_task_id),
        )

    return drafts


def sync_return_timeline(session: Session, return_id: str, *, commit: bool = True) -> int:
    """Materialize structured records into return_events (idempotent). Returns new rows inserted."""
    inserted = 0
    for draft in _drafts_from_structured_data(session, return_id):
        before = session.execute(
            select(ReturnEvent.event_id).where(
                ReturnEvent.return_id == return_id,
                ReturnEvent.event_type == draft.event_type,
                ReturnEvent.source_type == draft.source_type,
                ReturnEvent.source_id == draft.source_id,
            )
        ).scalar_one_or_none()
        record_return_event(
            session,
            return_id=return_id,
            event_type=draft.event_type,
            description=draft.description,
            source_type=draft.source_type,
            source_id=draft.source_id,
            event_timestamp=draft.event_timestamp,
            commit=False,
        )
        after = session.execute(
            select(ReturnEvent.event_id).where(
                ReturnEvent.return_id == return_id,
                ReturnEvent.event_type == draft.event_type,
                ReturnEvent.source_type == draft.source_type,
                ReturnEvent.source_id == draft.source_id,
            )
        ).scalar_one_or_none()
        if before is None and after is not None:
            inserted += 1
    if commit:
        session.commit()
    return inserted


def sync_all_return_timelines(session: Session, *, commit: bool = True) -> dict[str, int]:
    return_ids = session.execute(select(Return.return_id)).scalars().all()
    summary = {"returns": 0, "events_inserted": 0}
    for return_id in return_ids:
        summary["events_inserted"] += sync_return_timeline(session, return_id, commit=False)
        summary["returns"] += 1
    if commit:
        session.commit()
    return summary
