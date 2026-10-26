"""Supervisor approval queue service."""

from datetime import datetime, timedelta, timezone

from app.database.base import utc_now
from app.models.enums import ActionType, ApprovalStatus, ExecutionStatus
from app.models.tables import ActionRequest
from app.services.approvals import list_pending_approvals


def test_list_pending_approvals_age_with_naive_created_at(populated_db) -> None:
    naive_created = utc_now().replace(tzinfo=None) - timedelta(hours=2)
    populated_db.add(
        ActionRequest(
            return_id="R101",
            action_type=ActionType.CREATE_REPLACEMENT_REQUEST.value,
            requested_by="returns_analyst",
            approval_required=True,
            approval_status=ApprovalStatus.PENDING.value,
            execution_status=ExecutionStatus.PENDING.value,
            created_at=naive_created,
            idempotency_key="test-approvals-age-naive",
        )
    )
    populated_db.commit()

    payload = list_pending_approvals(populated_db, limit=20)
    ages = [a["age_minutes"] for a in payload["actions"] if a["return_id"] == "R101"]
    assert ages
    assert ages[0] is not None
    assert ages[0] >= 110
