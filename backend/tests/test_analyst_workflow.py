"""Returns analyst workflow (case at requested, queue stages)."""

from sqlalchemy import select

from app.models.enums import IssueType, ReturnStatus, UserRole
from app.models.tables import Return
from app.security.deps import CurrentUser
from app.services.analyst_queue import build_analyst_work_queue
from app.services.cases import create_case, get_active_case


def test_create_case_on_requested_return(populated_db) -> None:
    row = populated_db.execute(
        select(Return).where(Return.return_status == ReturnStatus.REQUESTED.value).limit(1)
    ).scalar_one_or_none()
    if row is None:
        return
    actor = CurrentUser(user_id=1, username="analyst", role=UserRole.RETURNS_ANALYST)
    existing = get_active_case(populated_db, row.return_id)
    if existing is not None:
        case = existing
    else:
        case = create_case(
            populated_db,
            return_id=row.return_id,
            issue_type=IssueType.MISSING_INSPECTION,
            priority="medium",
            actor=actor,
        )
    assert case.case_id
    populated_db.refresh(row)
    assert row.return_status == ReturnStatus.REQUESTED.value
    assert get_active_case(populated_db, row.return_id) is not None


def test_analyst_queue_await_warehouse_after_case(populated_db) -> None:
    row = populated_db.execute(
        select(Return).where(Return.return_status == ReturnStatus.REQUESTED.value).limit(1)
    ).scalar_one_or_none()
    if row is None:
        return
    actor = CurrentUser(user_id=2, username="analyst2", role=UserRole.RETURNS_ANALYST)
    if get_active_case(populated_db, row.return_id) is None:
        create_case(
            populated_db,
            return_id=row.return_id,
            issue_type=IssueType.GENERAL,
            priority="medium",
            actor=actor,
        )
    items = build_analyst_work_queue(populated_db, limit=200)
    item = next((i for i in items if i["return_id"] == row.return_id), None)
    assert item is not None
    assert item["workflow_stage"] == "await_warehouse"
