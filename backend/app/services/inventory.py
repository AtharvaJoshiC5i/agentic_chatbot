"""Inventory disposition reservations for returned units."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import InventoryDispositionStatus
from app.models.tables import InventoryDisposition, Return


class InventoryServiceError(Exception):
    def __init__(self, message: str, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code


_ACTIVE_DISPOSITIONS = frozenset(
    {
        InventoryDispositionStatus.RESERVED,
        InventoryDispositionStatus.IN_REPAIR,
        InventoryDispositionStatus.LISTED_FOR_SALE,
        InventoryDispositionStatus.SUPPLIER_RETURN,
        InventoryDispositionStatus.QUARANTINE,
    }
)


def reserve_disposition(
    session: Session,
    *,
    return_id: str,
    disposition: InventoryDispositionStatus,
    product_unit_id: int | None = None,
    recovery_task_id: int | None = None,
) -> InventoryDisposition:
    if session.get(Return, return_id) is None:
        raise InventoryServiceError("Return not found", "not_found")

    if product_unit_id is not None:
        conflict = session.execute(
            select(InventoryDisposition).where(
                InventoryDisposition.product_unit_id == product_unit_id,
                InventoryDisposition.disposition.in_([d.value for d in _ACTIVE_DISPOSITIONS]),
            )
        ).scalar_one_or_none()
        if conflict is not None and conflict.return_id != return_id:
            raise InventoryServiceError(
                "Product unit already reserved for another recovery workflow.",
                "disposition_conflict",
            )

    row = InventoryDisposition(
        return_id=return_id,
        product_unit_id=product_unit_id,
        disposition=disposition.value,
        recovery_task_id=recovery_task_id,
        actual_proceeds_paise=None,
        actual_cost_paise=None,
        created_at=utc_now(),
    )
    session.add(row)
    session.flush()
    return row
