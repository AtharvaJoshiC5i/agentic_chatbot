"""Refundable amount calculations (supports partial refunds)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import RefundStatus
from app.models.tables import OrderItem, Refund, Return


def calculate_refundable_amount_paise(
    session: Session,
    return_id: str,
    *,
    exclude_refund_id: int | None = None,
) -> dict[str, int]:
    return_row = session.get(Return, return_id)
    if return_row is None:
        raise ValueError("Return not found")
    item = session.get(OrderItem, return_row.order_item_id)
    if item is None:
        raise ValueError("Order item not found")

    line_total = item.unit_price * item.quantity
    refunded = session.execute(
        select(Refund).where(
            Refund.return_id == return_id,
            Refund.refund_status.in_(
                [
                    RefundStatus.COMPLETED.value,
                    RefundStatus.PROCESSING.value,
                    RefundStatus.APPROVED.value,
                ]
            ),
        )
    ).scalars().all()
    already = sum(
        r.refund_amount for r in refunded if exclude_refund_id is None or r.refund_id != exclude_refund_id
    )
    remaining = max(0, line_total - already)
    return {
        "line_total_paise": line_total,
        "already_refunded_paise": already,
        "remaining_refundable_paise": remaining,
    }
