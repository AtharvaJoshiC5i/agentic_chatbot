"""Warehouse inspection recording."""

from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import ActorType, InspectionResult, ProductCondition, ReturnStatus, SourceType
from app.models.tables import Inspection, OrderItem, Return
from app.security.deps import CurrentUser
from app.services.audit import record_audit
from app.services.return_events import record_return_event
from app.services.return_status import ReturnStatusError, on_inspection_recorded


class InspectionServiceError(Exception):
    def __init__(self, message: str, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code


def record_inspection(
    session: Session,
    *,
    return_id: str,
    product_condition: ProductCondition,
    returned_serial_number: str | None,
    accessories_complete: bool,
    defect_verified: bool,
    inspection_result: InspectionResult,
    inspector_notes: str | None,
    actor: CurrentUser,
) -> Inspection:
    return_row = session.get(Return, return_id)
    if return_row is None:
        raise InspectionServiceError("Return not found", "not_found")

    if return_row.received_date is None:
        raise InspectionServiceError(
            "Record warehouse receipt after confirming physical arrival before inspection.",
            "not_received",
        )
    if return_row.return_status not in (
        ReturnStatus.RECEIVED.value,
        ReturnStatus.INSPECTING.value,
        ReturnStatus.INVESTIGATING.value,
    ):
        raise InspectionServiceError(
            "Return must be in a received warehouse status before inspection.",
            "not_received",
        )

    item = session.get(OrderItem, return_row.order_item_id)
    purchased = item.purchased_serial_number if item else None
    if purchased and returned_serial_number and purchased != returned_serial_number:
        # Recording the mismatch is the warehouse's job: it is the evidence the analyst and supervisor need.
        mismatch_note = f"Serial mismatch: purchased {purchased}, received {returned_serial_number}. Additional verification required."
        inspector_notes = f"{inspector_notes}\n{mismatch_note}" if inspector_notes else mismatch_note
        if inspection_result == InspectionResult.PASS:
            inspection_result = InspectionResult.INCONCLUSIVE

    row = Inspection(
        return_id=return_id,
        inspection_date=utc_now(),
        returned_serial_number=returned_serial_number,
        product_condition=product_condition.value,
        accessories_complete=accessories_complete,
        defect_verified=defect_verified,
        inspection_result=inspection_result.value,
        inspector_notes=inspector_notes,
    )
    session.add(row)
    session.flush()
    on_inspection_recorded(session, return_id, row.inspection_id, actor)
    record_return_event(
        session,
        return_id=return_id,
        event_type="inspection_completed",
        description=f"Inspection {row.inspection_id} recorded ({inspection_result.value}).",
        source_type=SourceType.INSPECTION.value,
        source_id=str(row.inspection_id),
        event_timestamp=row.inspection_date,
    )
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="record_inspection",
        target_entity="inspection",
        target_id=str(row.inspection_id),
        execution_result="succeeded",
        evidence_references={"return_id": return_id},
    )
    session.commit()
    from app.services.handoff import claim_case_for_warehouse

    claim_case_for_warehouse(session, return_id, actor)
    session.refresh(row)
    return row
