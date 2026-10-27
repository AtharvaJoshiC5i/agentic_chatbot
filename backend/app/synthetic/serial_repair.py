"""One-off alignment: single-qty order lines vs product_units serial suffixes."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import OrderItem, ProductUnit


def align_single_quantity_product_unit_serials(session: Session) -> int:
    """
    Bulk generator used ``SN######-1`` while order lines store ``SN######`` for qty=1.
    Normalize so get_product_unit(purchased_serial) succeeds after reload.
    """
    fixed = 0
    items = session.execute(
        select(OrderItem).where(OrderItem.purchased_serial_number.isnot(None))
    ).scalars().all()
    for item in items:
        if (item.quantity or 0) != 1:
            continue
        units = (
            session.execute(select(ProductUnit).where(ProductUnit.order_item_id == item.order_item_id))
            .scalars()
            .all()
        )
        if len(units) != 1:
            continue
        unit = units[0]
        purchased = item.purchased_serial_number
        if not purchased or unit.serial_number == purchased:
            continue
        if unit.serial_number == f"{purchased}-1":
            unit.serial_number = purchased
            fixed += 1
    if fixed:
        session.commit()
    return fixed
