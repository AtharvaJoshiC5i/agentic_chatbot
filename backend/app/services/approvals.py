"""Cross-return approval queues for supervisors."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import as_utc, utc_now
from app.models.enums import ApprovalStatus, RefundStatus
from app.models.tables import ActionRequest, Refund


def list_pending_approvals(session: Session, limit: int = 100) -> dict[str, list[dict]]:
    session.expire_all()
    now = utc_now()
    refunds = session.execute(
        select(Refund)
        .where(
            Refund.refund_status == RefundStatus.REQUESTED.value,
            Refund.approval_status == ApprovalStatus.PENDING.value,
        )
        .order_by(Refund.refund_id.desc())
        .limit(limit)
    ).scalars().all()
    actions = session.execute(
        select(ActionRequest)
        .where(ActionRequest.approval_status == ApprovalStatus.PENDING.value)
        .order_by(ActionRequest.action_id.desc())
        .limit(limit)
    ).scalars().all()

    def age(created: datetime | None) -> int | None:
        if created is None:
            return None
        return int((now - as_utc(created)).total_seconds() // 60)

    from app.models.tables import ReplacementRequest

    replacements = session.execute(
        select(ReplacementRequest)
        .where(ReplacementRequest.status == "requested")
        .order_by(ReplacementRequest.replacement_id.desc())
        .limit(limit)
    ).scalars().all()

    return {
        "replacements": [
            {
                "replacement_id": r.replacement_id,
                "return_id": r.return_id,
                "requester": r.requested_by,
                "age_minutes": age(r.created_at),
                "kind": "replacement",
            }
            for r in replacements
        ],
        "refunds": [
            {
                "refund_id": r.refund_id,
                "return_id": r.return_id,
                "amount_paise": r.refund_amount,
                "requester": None,
                "age_minutes": None,
                "kind": "refund",
            }
            for r in refunds
        ],
        "actions": [
            {
                "action_id": a.action_id,
                "return_id": a.return_id,
                "action_type": a.action_type,
                "requested_by": a.requested_by,
                "age_minutes": age(a.created_at),
                "kind": "action",
            }
            for a in actions
        ],
    }
