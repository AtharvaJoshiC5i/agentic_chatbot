"""Customer notifications: drafted automatically after a decision, confirmed by the returns analyst.

"Sent" means the analyst reviewed the message and confirmed it: it is logged on the return timeline and in
the audit trail. No mail server is called (customer addresses in this dataset use the .invalid domain).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import ActorType, SourceType
from app.models.tables import Customer, CustomerNotification, Order, OrderItem, Product, Return
from app.security.deps import CurrentUser
from app.services.audit import record_audit
from app.services.return_events import record_return_event


class NotificationError(Exception):
    def __init__(self, message: str, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code


KINDS = ("refund_approved", "refund_rejected", "replacement_approved", "replacement_rejected", "declined")

_TEMPLATES: dict[str, tuple[str, str]] = {
    "refund_approved": (
        "Your refund for {product} has been approved",
        "We have reviewed your return {return_id} and approved your refund of {amount}.\n"
        "This demo records the refund decision locally; no payment was transferred.",
    ),
    "refund_rejected": (
        "Update on your return {return_id}",
        "We have reviewed your return {return_id} for {product}. Unfortunately we are unable to approve a refund.\n"
        "Reason: {reason}\nIf you believe this is a mistake, reply to this email and we will look at it again.",
    ),
    "replacement_approved": (
        "Your replacement for {product} has been approved",
        "We have reviewed your return {return_id} and approved a replacement for {product}.\n"
        "We will email you the dispatch details as soon as it ships.",
    ),
    "replacement_rejected": (
        "Update on your return {return_id}",
        "We have reviewed your return {return_id} for {product}. Unfortunately we are unable to send a replacement.\n"
        "Reason: {reason}\nReply to this email if you would like to discuss other options.",
    ),
    "declined": (
        "Update on your return {return_id}",
        "We have reviewed your return {return_id} for {product}. Unfortunately we are unable to proceed with your request.\n"
        "Reason: {reason}\nIf you have more information, reply to this email and we will review it again.",
    ),
}


def _customer_context(session: Session, return_id: str) -> dict:
    row = session.get(Return, return_id)
    if row is None:
        raise NotificationError("Return not found", "not_found")
    item = session.get(OrderItem, row.order_item_id)
    order = session.get(Order, item.order_id) if item else None
    customer = session.get(Customer, order.customer_id) if order else None
    product = session.get(Product, item.product_id) if item else None
    if customer is None:
        raise NotificationError("No customer record for this return", "no_customer")
    return {
        "email": customer.email,
        "name": customer.customer_name,
        "product": product.product_name if product else "your item",
        "order_id": order.order_id if order else "",
    }


def draft_notification(
    session: Session,
    *,
    return_id: str,
    kind: str,
    actor: CurrentUser,
    reason: str | None = None,
    amount_paise: int | None = None,
) -> CustomerNotification:
    if kind not in KINDS:
        raise NotificationError(f"Unknown notification kind {kind}", "invalid_kind")
    existing = session.execute(
        select(CustomerNotification).where(
            CustomerNotification.return_id == return_id,
            CustomerNotification.kind == kind,
            CustomerNotification.status == "draft",
        )
    ).scalars().first()
    if existing is not None:
        return existing

    ctx = _customer_context(session, return_id)
    subject_tpl, body_tpl = _TEMPLATES[kind]
    values = {
        "return_id": return_id,
        "product": ctx["product"],
        "reason": (reason or "Not specified").strip(),
        "amount": f"INR {(amount_paise or 0) / 100:,.2f}",
    }
    body = f"Dear {ctx['name']},\n\n{body_tpl.format(**values)}\n\nRegards,\nShopSphere Customer Care"
    note = CustomerNotification(
        return_id=return_id,
        kind=kind,
        to_email=ctx["email"],
        subject=subject_tpl.format(**values),
        body=body,
        status="draft",
        created_by=actor.username,
        created_at=utc_now(),
    )
    session.add(note)
    session.flush()
    record_return_event(
        session,
        return_id=return_id,
        event_type="other",
        description=f"Customer message drafted ({kind}); waiting for the returns analyst to confirm.",
        source_type=SourceType.SYSTEM.value,
        source_id=f"notification:{note.notification_id}:drafted",
    )
    return note


def notification_to_dict(n: CustomerNotification) -> dict:
    return {
        "notification_id": n.notification_id,
        "return_id": n.return_id,
        "kind": n.kind,
        "to_email": n.to_email,
        "subject": n.subject,
        "body": n.body,
        "status": n.status,
        "created_by": n.created_by,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "sent_by": n.sent_by,
        "sent_at": n.sent_at.isoformat() if n.sent_at else None,
    }


def list_notifications(
    session: Session, *, status: str | None = None, return_id: str | None = None, limit: int = 100
) -> list[CustomerNotification]:
    query = select(CustomerNotification).order_by(CustomerNotification.notification_id.desc()).limit(limit)
    if status:
        query = query.where(CustomerNotification.status == status)
    if return_id:
        query = query.where(CustomerNotification.return_id == return_id.upper())
    return list(session.execute(query).scalars().all())


def send_notification(
    session: Session,
    *,
    notification_id: int,
    actor: CurrentUser,
    subject: str | None = None,
    body: str | None = None,
) -> CustomerNotification:
    """Analyst confirms the message: it is logged as sent and the case and return are closed."""
    from app.models.enums import CaseStatus
    from app.models.tables import InvestigationCase
    from app.services.handoff import advance_case
    from app.services.return_status import ReturnStatusError, close_return

    note = session.get(CustomerNotification, notification_id)
    if note is None:
        raise NotificationError("Notification not found", "not_found")
    if note.status == "sent":
        raise NotificationError("This message was already sent.", "already_sent")
    if subject is not None and subject.strip():
        note.subject = subject.strip()[:255]
    if body is not None and body.strip():
        note.body = body.strip()
    note.status = "sent"
    note.sent_by = actor.username
    note.sent_at = utc_now()
    record_return_event(
        session,
        return_id=note.return_id,
        event_type="other",
        description=f"Customer message confirmation recorded by {actor.username} ({note.kind}); no email was sent.",
        source_type=SourceType.SYSTEM.value,
        source_id=f"notification:{note.notification_id}:sent",
        event_timestamp=note.sent_at,
    )
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="send_customer_notification",
        target_entity="customer_notification",
        target_id=str(note.notification_id),
        execution_result="succeeded",
        evidence_references={"return_id": note.return_id, "kind": note.kind},
    )
    # Close the loop: resolved cases become closed and the return is closed once nothing else is waiting.
    case = session.execute(
        select(InvestigationCase)
        .where(InvestigationCase.return_id == note.return_id, InvestigationCase.case_status == CaseStatus.RESOLVED.value)
        .order_by(InvestigationCase.case_id.desc())
    ).scalars().first()
    if case is not None:
        advance_case(session, case, [CaseStatus.CLOSED], actor)
    pending = session.execute(
        select(CustomerNotification).where(
            CustomerNotification.return_id == note.return_id,
            CustomerNotification.status == "draft",
            CustomerNotification.notification_id != note.notification_id,
        )
    ).first()
    if pending is None:
        try:
            close_return(session, note.return_id, actor, description=f"Return closed after message confirmation was recorded by {actor.username}; no email was sent.")
        except ReturnStatusError:
            pass  # not in a closable state (for example still being worked): leave it
    session.commit()
    session.refresh(note)
    return note
