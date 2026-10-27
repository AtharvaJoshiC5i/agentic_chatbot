"""Cross-persona workflow snapshot stays in sync as each persona completes their step."""

from sqlalchemy import select

from app.models.enums import InspectionResult, IssueType, ProductCondition, ReturnStatus, UserRole
from app.models.tables import Return
from app.security.deps import CurrentUser
from app.services.cases import create_case, get_active_case
from app.services.handoff import record_verdict
from app.services.inspections import InspectionServiceError, record_inspection
from app.services.return_status import receive_return_at_warehouse
from app.services.return_workflow import build_return_workflow_snapshot
from app.services.warehouse_handoff import get_warehouse_handoff_status


def test_inspection_cannot_implicitly_record_warehouse_receipt(populated_db) -> None:
    row = populated_db.execute(
        select(Return)
        .where(Return.return_status == ReturnStatus.REQUESTED.value, Return.received_date.is_(None))
        .limit(1)
    ).scalar_one_or_none()
    assert row is not None

    try:
        record_inspection(
            populated_db,
            return_id=row.return_id,
            product_condition=ProductCondition.DEFECTIVE,
            returned_serial_number=None,
            accessories_complete=True,
            defect_verified=True,
            inspection_result=InspectionResult.PASS,
            inspector_notes="Must not create a receipt implicitly",
            actor=CurrentUser(user_id=2, username="wf_wh", role=UserRole.WAREHOUSE_MANAGER),
        )
    except InspectionServiceError as exc:
        assert exc.code == "not_received"
    else:
        raise AssertionError("Inspection unexpectedly created a receipt")

    populated_db.expire_all()
    persisted = populated_db.get(Return, row.return_id)
    assert persisted is not None and persisted.received_date is None


def test_workflow_follows_each_persona_step(populated_db) -> None:
    row = populated_db.execute(
        select(Return)
        .where(Return.return_status == ReturnStatus.REQUESTED.value, Return.requested_resolution == "refund")
        .limit(1)
    ).scalar_one_or_none()
    assert row is not None
    rid = row.return_id
    analyst = CurrentUser(user_id=1, username="wf_analyst", role=UserRole.RETURNS_ANALYST)
    wh = CurrentUser(user_id=2, username="wf_wh", role=UserRole.WAREHOUSE_MANAGER)

    assert build_return_workflow_snapshot(populated_db, rid)["analyst_workflow_stage"] == "investigate"
    if get_active_case(populated_db, rid) is None:
        create_case(populated_db, return_id=rid, issue_type=IssueType.GENERAL, priority="medium", actor=analyst)
    snap = build_return_workflow_snapshot(populated_db, rid)
    assert snap["analyst_workflow_stage"] == "await_warehouse" and snap["next_owner"] == "warehouse_manager"

    receive_return_at_warehouse(populated_db, rid, wh)
    record_inspection(
        populated_db,
        return_id=rid,
        product_condition=ProductCondition.DEFECTIVE,
        returned_serial_number=None,
        accessories_complete=True,
        defect_verified=True,
        inspection_result=InspectionResult.PASS,
        inspector_notes="Workflow sync test",
        actor=wh,
    )
    populated_db.expire_all()
    # An inspection alone is not the warehouse's answer: the verdict is.
    snap = build_return_workflow_snapshot(populated_db, rid)
    assert snap["inspection_count"] >= 1 and snap["warehouse_work_complete"] is False
    assert snap["analyst_workflow_stage"] == "await_warehouse"
    assert get_warehouse_handoff_status(populated_db, rid)["warehouse_queue_stage"] == "verdict"

    record_verdict(populated_db, return_id=rid, actor=wh, feasible=True, recommendation="proceed", notes=None)
    populated_db.expire_all()
    snap = build_return_workflow_snapshot(populated_db, rid)
    assert snap["warehouse_work_complete"] is True
    assert snap["analyst_workflow_stage"] == "submit_refund" and snap["next_owner"] == "returns_analyst"
    assert "refund can be performed" in snap["status_summary"]
    assert snap["warehouse_verdict"]["recommendation"] == "proceed"
    assert get_warehouse_handoff_status(populated_db, rid)["warehouse_queue_stage"] == "verdict_given"
