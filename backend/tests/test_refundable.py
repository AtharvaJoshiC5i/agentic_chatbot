"""Refundable amount calculations."""

from app.models.enums import ApprovalStatus, RefundStatus, UserRole
from app.models.tables import Refund
from app.security.deps import CurrentUser
from app.security.passwords import hash_password
from app.services.refundable import calculate_refundable_amount_paise
from app.services.refunds import approve_refund, execute_refund, request_refund


def test_execute_refund_succeeds_when_refund_is_approved(populated_db) -> None:
    from app.models.tables import User

    populated_db.add(
        User(
            username="ref_super",
            password_hash=hash_password("pass"),
            role=UserRole.RETURNS_SUPERVISOR.value,
            active=True,
        )
    )
    populated_db.commit()
    actor = CurrentUser(user_id=1, username="ref_super", role=UserRole.RETURNS_SUPERVISOR)

    from tests.workflow_helpers import prepare_for_submission

    prepare_for_submission(populated_db, "R105")
    refund = request_refund(
        populated_db,
        return_id="R105",
        refund_amount_paise=100_000,
        idempotency_key="test-r105-refund-exec-1",
        actor=actor,
    )
    completed = approve_refund(populated_db, refund.refund_id, actor, approve=True)  # approval pays out
    assert completed.refund_status == RefundStatus.COMPLETED

    amounts = calculate_refundable_amount_paise(
        populated_db, "R105", exclude_refund_id=completed.refund_id
    )
    assert amounts["remaining_refundable_paise"] >= 0
