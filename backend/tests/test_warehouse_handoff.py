"""Warehouse handoff status (queue-aligned)."""

from app.models.enums import IssueType, ReturnStatus, UserRole
from app.security.deps import CurrentUser
from app.services.cases import create_case
from app.services.warehouse_handoff import get_warehouse_handoff_status


def test_handoff_shows_active_case_after_analyst_creates(populated_db) -> None:
    from sqlalchemy import select

    from app.models.tables import Return

    row = populated_db.execute(
        select(Return).where(Return.return_status == ReturnStatus.REQUESTED.value).limit(1)
    ).scalar_one_or_none()
    if row is None:
        return
    actor = CurrentUser(user_id=1, username="analyst_wh", role=UserRole.RETURNS_ANALYST)
    create_case(
        populated_db,
        return_id=row.return_id,
        issue_type=IssueType.GENERAL,
        priority="medium",
        actor=actor,
    )
    status = get_warehouse_handoff_status(populated_db, row.return_id)
    assert status["analyst_case_open"] is True
    assert status["active_case"] is not None
    assert status["active_case"]["case_id"]
    assert status["warehouse_queue_stage"] == "receive"
    assert status["inspection_count"] == 0
