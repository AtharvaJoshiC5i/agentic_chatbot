"""Investigation case workflow tests."""

from app.models.enums import IssueType, UserRole
from app.models.tables import User
from app.security.deps import CurrentUser
from app.security.passwords import hash_password
from app.services.cases import CaseServiceError, create_case, get_active_case


def test_duplicate_case_reuse_active(populated_db) -> None:
    actor = CurrentUser(user_id=1, username="analyst", role=UserRole.RETURNS_ANALYST)
    first = create_case(
        populated_db,
        return_id="R102",
        issue_type=IssueType.SERIAL_MISMATCH,
        priority="high",
        actor=actor,
    )
    second = create_case(
        populated_db,
        return_id="R102",
        issue_type=IssueType.GENERAL,
        priority="low",
        actor=actor,
        reuse_active=True,
    )
    assert second.case_id == first.case_id
    assert get_active_case(populated_db, "R102") is not None


def test_duplicate_case_raises_when_disabled(populated_db) -> None:
    actor = CurrentUser(user_id=1, username="analyst2", role=UserRole.RETURNS_ANALYST)
    create_case(
        populated_db,
        return_id="R102",
        issue_type=IssueType.POLICY_EXCEPTION,
        priority="medium",
        actor=actor,
    )
    try:
        create_case(
            populated_db,
            return_id="R102",
            issue_type=IssueType.GENERAL,
            priority="low",
            actor=actor,
            reuse_active=False,
        )
        raised = False
    except CaseServiceError as exc:
        raised = True
        assert exc.code == "duplicate_case"
    assert raised
