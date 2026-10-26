"""Operator-facing response formatting."""

from app.agents.operator_response import format_inr_from_paise, format_operator_response
from app.models.enums import UserRole


def test_format_inr_from_paise() -> None:
    assert format_inr_from_paise(151595) == "₹1,515.95"


def test_humanizes_r101_style_wall_of_jargon() -> None:
    raw = """Investigation Summary for Return R101
Eligibility Status: Eligible

Policy Check: The return request was made 5 days after delivery.
Investigation Result: Phase 8 investigation (run_return_investigation) reported no_inconsistency_detected with an outcome of eligible_for_standard_resolution.
Refund Action Taken:

Based on the expected net recovery value (151,595 paise), a refund request has been successfully submitted under action ID 1.
Status: Currently pending supervisor approval and has not been executed yet, as requested."""

    out = format_operator_response(raw, role=UserRole.RETURNS_ANALYST)

    assert "run_return_investigation" not in out
    assert "151,595 paise" not in out
    assert "₹1,515.95" in out
    assert "request #1" in out.lower()
    assert "eligible for a standard refund" in out.lower()
    assert "no red flags" in out.lower()


def test_build_system_prompt_includes_operator_structure() -> None:
    from app.agents.prompts import build_system_prompt
    from app.security.deps import CurrentUser

    user = CurrentUser(user_id=1, username="support_agent", role=UserRole.CUSTOMER_SUPPORT)
    prompt = build_system_prompt(user)
    assert "answer the question first" in prompt.lower()
    assert "never mention these names in your final reply" in prompt.lower()
    assert "customer support" in prompt.lower()

    sup = CurrentUser(user_id=2, username="returns_supervisor", role=UserRole.RETURNS_SUPERVISOR)
    sup_prompt = build_system_prompt(sup)
    assert "supervisor_pending" in sup_prompt.lower()
