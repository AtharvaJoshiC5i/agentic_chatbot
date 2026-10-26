"""Test helper: put a return through the analyst -> warehouse hand-off so a refund or replacement may be submitted."""

from __future__ import annotations

from app.models.enums import InspectionResult, IssueType, ProductCondition, UserRole
from app.security.deps import CurrentUser
from app.services.cases import create_case, get_active_case
from app.services.handoff import get_latest_verdict, record_verdict
from app.services.inspections import record_inspection
from app.services.return_status import receive_return_at_warehouse
from app.services.warehouse_handoff import get_warehouse_handoff_status

ANALYST = CurrentUser(user_id=9001, username="helper_analyst", role=UserRole.RETURNS_ANALYST)
WAREHOUSE = CurrentUser(user_id=9002, username="helper_warehouse", role=UserRole.WAREHOUSE_MANAGER)


def prepare_for_submission(db, return_id: str) -> None:
    """Open a case, receive and inspect the unit if needed, and record a 'proceed' warehouse verdict."""
    if get_active_case(db, return_id) is None:
        create_case(db, return_id=return_id, issue_type=IssueType.GENERAL, priority="medium", actor=ANALYST)
    receive_return_at_warehouse(db, return_id, WAREHOUSE)
    if get_warehouse_handoff_status(db, return_id)["inspection_count"] == 0:
        record_inspection(
            db,
            return_id=return_id,
            product_condition=ProductCondition.DAMAGED,
            returned_serial_number=None,
            accessories_complete=True,
            defect_verified=True,
            inspection_result=InspectionResult.PASS,
            inspector_notes="helper inspection",
            actor=WAREHOUSE,
        )
    if get_latest_verdict(db, return_id) is None:
        record_verdict(db, return_id=return_id, actor=WAREHOUSE, feasible=True, recommendation="proceed", notes=None)
