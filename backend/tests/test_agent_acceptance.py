"""Deterministic acceptance scenarios (no live LLM)."""

from app.agents.context import clear_agent_context, set_agent_context
from app.investigation.evidence_summary import detect_return_inconsistencies
from app.investigation.investigation import run_investigation
from app.models.enums import UserRole
from app.security.deps import CurrentUser
from app.services.cases import create_case, get_active_case
from app.services.decision_passport import save_decision_passport
from app.services.escalations import create_escalation
from app.services.monitoring import run_monitoring_checks
from app.services.recovery_optimizer import optimize_recovery
from app.services.refunds import get_refund_for_return
from app.models.enums import IssueType, RefundStatus
from app.services.actions import ActionServiceError, submit_action
from app.models.enums import ActionType, ActorType


def test_scenario_b_r102_serial_mismatch_signal(populated_db) -> None:
    report = run_investigation(populated_db, "R102")
    assert report is not None
    assert report.f2_signal == "additional_verification_required"


def test_scenario_c_r106_no_duplicate_refund(populated_db) -> None:
    refund = get_refund_for_return(populated_db, "R106")
    assert refund is not None
    assert refund.refund_status == RefundStatus.COMPLETED.value
    actor = CurrentUser(user_id=1, username="acc", role=UserRole.RETURNS_ANALYST)
    try:
        submit_action(
            populated_db,
            action_type=ActionType.REQUEST_REFUND,
            return_id="R106",
            payload={"return_id": "R106", "refund_amount_paise": 100, "refund_idempotency_key": "dup-test"},
            idempotency_key="acc-r106-wrap",
            actor=actor,
            actor_type=ActorType.USER,
            auto_execute=False,
        )
        blocked = False
    except ActionServiceError as exc:
        blocked = exc.code == "duplicate_refund"
    assert blocked


def test_scenario_d_r108_recovery(populated_db) -> None:
    rec = optimize_recovery(populated_db, "R108")
    assert rec.recommended_method == "repair_and_resell"


def test_scenario_e_r115_unsafe(populated_db) -> None:
    rec = optimize_recovery(populated_db, "R115")
    assert rec.unsafe_product is True


def test_scenario_8_escalation_dedup(populated_db) -> None:
    first = create_escalation(
        populated_db,
        related_entity="return",
        related_id="R113",
        escalation_reason="awaiting_inspection",
    )
    second = create_escalation(
        populated_db,
        related_entity="return",
        related_id="R113",
        escalation_reason="awaiting_inspection",
    )
    assert first.escalation_id == second.escalation_id
    run_monitoring_checks(populated_db, commit=True)


def test_decision_passport_persists(populated_db) -> None:
    passport = save_decision_passport(populated_db, "R102")
    assert passport.passport_id > 0
    assert "R102" in passport.markdown_report


def test_r102_case_creation_idempotent(populated_db) -> None:
    actor = CurrentUser(user_id=1, username="acc2", role=UserRole.RETURNS_ANALYST)
    case = create_case(
        populated_db,
        return_id="R102",
        issue_type=IssueType.SERIAL_MISMATCH,
        priority="high",
        actor=actor,
    )
    again = create_case(
        populated_db,
        return_id="R102",
        issue_type=IssueType.GENERAL,
        priority="low",
        actor=actor,
    )
    assert again.case_id == case.case_id
    assert get_active_case(populated_db, "R102") is not None


def test_r110_contradiction_tool(populated_db) -> None:
    summary = detect_return_inconsistencies(populated_db, "R110")
    assert summary["primary_signal"] == "conflicting_inspection_findings"
    assert summary["disputed"] or summary["gaps"]
