"""Agent tools respect the three demo personas (no LLM involved)."""

from app.security.permissions import DEMO_LOGIN_ROLES

import json

import pytest

from app.agents.context import clear_agent_context, set_agent_context
from app.models.enums import UserRole
from app.security.deps import CurrentUser
from app.synthetic.generator import generate_synthetic_data
from app.synthetic.loader import load_bundle
from app.tools.action_tools import (
    approve_action_request,
    assign_investigation_case,
    submit_inspection_task,
    submit_refund_request,
    submit_refurbishment_task,
)
from app.tools.portfolio_tools import (
    get_monitoring_overview,
    list_actions_for_return,
    list_open_investigation_cases,
    list_refunds_awaiting_approval,
    list_returns,
)


@pytest.fixture()
def seeded(db_session):
    load_bundle(db_session, generate_synthetic_data())
    yield db_session
    clear_agent_context()


def _as(session, role: UserRole) -> None:
    set_agent_context(session, CurrentUser(user_id=1, username=role.value, role=role))


def _run(tool, **kwargs) -> dict:
    return json.loads(tool.invoke(kwargs))


def test_portfolio_tools_work_for_every_role(seeded) -> None:
    for role in DEMO_LOGIN_ROLES:
        _as(seeded, role)
        assert _run(list_returns, status="investigating", limit=3)["count"] == 3
        assert _run(list_refunds_awaiting_approval, limit=3)["count_returned"] == 3
        assert _run(list_open_investigation_cases, overdue_only=True, limit=3)["cases"]
        assert "actions" in _run(list_actions_for_return, return_id="R101")
        assert "open_alerts" in _run(get_monitoring_overview)


def test_case_assignment_is_supervisor_only(seeded) -> None:
    for role in (UserRole.RETURNS_ANALYST, UserRole.WAREHOUSE_MANAGER):
        _as(seeded, role)
        assert _run(assign_investigation_case, case_id=1, assigned_to="analyst_03")["error"] == "forbidden"
    for role in (UserRole.RETURNS_SUPERVISOR,):
        _as(seeded, role)
        assert _run(assign_investigation_case, case_id=1, assigned_to="analyst_03")["assigned_to"] == "analyst_03"


def test_action_approval_is_supervisor_only(seeded) -> None:
    _as(seeded, UserRole.WAREHOUSE_MANAGER)
    action = _run(submit_refurbishment_task, return_id="R108", idempotency_key="role-test-r108")
    assert action["approval_status"] == "pending"
    assert "error" in _run(approve_action_request, action_id=action["action_id"])
    _as(seeded, UserRole.RETURNS_SUPERVISOR)
    assert _run(approve_action_request, action_id=action["action_id"])["approval_status"] == "approved"


def test_recovery_style_tasks_are_warehouse_and_supervisor(seeded) -> None:
    for role in (UserRole.RETURNS_ANALYST,):
        _as(seeded, role)
        assert _run(submit_inspection_task, return_id="R113")["error"] == "forbidden"
        assert _run(submit_refurbishment_task, return_id="R108")["error"] == "forbidden"
    for role in (UserRole.WAREHOUSE_MANAGER, UserRole.RETURNS_SUPERVISOR):
        _as(seeded, role)
        assert "error" not in _run(submit_inspection_task, return_id="R113", idempotency_key=f"t-insp-{role.value}")
        assert "error" not in _run(submit_refurbishment_task, return_id="R108", idempotency_key=f"t-refu-{role.value}")


def test_refund_request_is_blocked_for_warehouse_and_for_duplicates(seeded) -> None:
    _as(seeded, UserRole.WAREHOUSE_MANAGER)
    assert _run(submit_refund_request, return_id="R101", refund_amount_paise=1000, idempotency_key="wh-refund-1")["error"] == "forbidden"
    _as(seeded, UserRole.RETURNS_ANALYST)
    assert _run(submit_refund_request, return_id="R106", refund_amount_paise=249900, idempotency_key="dup-r106-1")["error"] == "duplicate_refund"


def test_summarize_returns_groups_for_every_role(seeded) -> None:
    from app.tools.portfolio_tools import summarize_returns

    for role in DEMO_LOGIN_ROLES:
        _as(seeded, role)
        data = _run(summarize_returns, group_by="reason")
        assert data["groups"] and sum(g["returns"] for g in data["groups"]) <= 500
        assert _run(summarize_returns, group_by="supplier")["groups"]
        assert _run(summarize_returns, group_by="nonsense")["error"] == "invalid_group_by"
