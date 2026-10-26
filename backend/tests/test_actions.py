"""Phase 10 action lifecycle tests."""

import json

from fastapi.testclient import TestClient

from tests.workflow_helpers import prepare_for_submission

from app.agents.context import clear_agent_context, set_agent_context
from app.main import app
from app.models.enums import UserRole
from app.models.tables import User
from app.security.deps import CurrentUser
from app.security.passwords import hash_password
from app.tools.action_tools import submit_refund_request

client = TestClient(app)


def _seed(db, username: str, role: UserRole, password: str = "action-pass") -> None:
    db.add(
        User(
            username=username,
            password_hash=hash_password(password),
            role=role.value,
            active=True,
        )
    )
    db.commit()


def _auth(username: str, password: str = "action-pass") -> dict[str, str]:
    token = client.post("/api/auth/login", json={"username": username, "password": password}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_refund_action_requires_approval_then_execute(populated_db) -> None:
    prepare_for_submission(populated_db, "R101")
    _seed(populated_db, "act_analyst", UserRole.RETURNS_ANALYST)
    _seed(populated_db, "act_super", UserRole.RETURNS_SUPERVISOR)
    analyst = _auth("act_analyst")
    supervisor = _auth("act_super")

    submit = client.post(
        "/api/actions",
        headers=analyst,
        json={
            "action_type": "request_refund",
            "return_id": "R101",
            "payload": {
                "return_id": "R101",
                "refund_amount_paise": 100000,
                "refund_idempotency_key": "action-r101-refund-1",
            },
            "idempotency_key": "action-wrap-r101-refund-1",
            "auto_execute": True,
        },
    )
    assert submit.status_code == 201, submit.text
    body = submit.json()
    # The request itself needs no separate approval: the supervisor decides once, on the refund.
    assert body["approval_status"] == "not_required"
    assert body["execution_status"] == "succeeded"

    refund_row = client.get("/api/returns/R101/refund", headers=supervisor).json()
    assert refund_row["refund_status"] == "requested" and refund_row["approval_status"] == "pending"
    approve = client.post(
        f"/api/refunds/{refund_row['refund_id']}/approve",
        headers=supervisor,
        json={"approve": True},
    )
    assert approve.status_code == 200
    assert approve.json()["refund_status"] == "completed"


def test_create_case_action_executes_immediately(populated_db) -> None:
    _seed(populated_db, "act_analyst2", UserRole.RETURNS_ANALYST)
    headers = _auth("act_analyst2")
    response = client.post(
        "/api/actions",
        headers=headers,
        json={
            "action_type": "create_case",
            "return_id": "R101",
            "payload": {"issue_type": "general", "priority": "low"},
            "idempotency_key": "action-case-r101-1",
        },
    )
    assert response.status_code == 201
    assert response.json()["execution_status"] == "succeeded"


def test_create_case_action_accepts_inspection_needed_alias(populated_db) -> None:
    _seed(populated_db, "act_analyst_alias", UserRole.RETURNS_ANALYST)
    headers = _auth("act_analyst_alias")
    response = client.post(
        "/api/actions",
        headers=headers,
        json={
            "action_type": "create_case",
            "return_id": "R103",
            "payload": {"issue_type": "inspection_needed", "priority": "medium"},
            "idempotency_key": "action-case-r103-alias-1",
        },
    )
    assert response.status_code == 201
    assert response.json()["execution_status"] == "succeeded"
    cases = client.get("/api/cases", headers=headers).json()["items"]
    match = [c for c in cases if c["return_id"] == "R103"]
    assert match
    assert match[0]["issue_type"] == "missing_inspection"


def test_r106_refund_execute_action_fails(populated_db) -> None:
    _seed(populated_db, "act_super2", UserRole.RETURNS_SUPERVISOR)
    headers = _auth("act_super2")
    refund = client.get("/api/returns/R106/refund", headers=headers).json()
    assert refund is not None

    submit = client.post(
        "/api/actions",
        headers=headers,
        json={
            "action_type": "execute_refund",
            "payload": {"refund_id": refund["refund_id"]},
            "idempotency_key": "action-exec-r106-dup",
            "auto_execute": False,
        },
    )
    assert submit.status_code == 201
    action_id = submit.json()["action_id"]

    client.post(f"/api/actions/{action_id}/approve", headers=headers, json={"approve": True})
    execute = client.post(f"/api/actions/{action_id}/execute", headers=headers)
    assert execute.status_code == 409


def test_second_refund_request_blocked_while_open(populated_db) -> None:
    prepare_for_submission(populated_db, "R104")
    _seed(populated_db, "act_analyst3", UserRole.RETURNS_ANALYST)
    headers = _auth("act_analyst3")
    first = client.post(
        "/api/actions",
        headers=headers,
        json={
            "action_type": "request_refund",
            "return_id": "R104",
            "payload": {
                "return_id": "R104",
                "refund_amount_paise": 50000,
                "refund_idempotency_key": "action-r104-refund-open",
            },
            "idempotency_key": "action-wrap-r104-refund-open",
        },
    )
    assert first.status_code == 201
    second = client.post(
        "/api/actions",
        headers=headers,
        json={
            "action_type": "request_refund",
            "return_id": "R104",
            "payload": {
                "return_id": "R104",
                "refund_amount_paise": 50000,
                "refund_idempotency_key": "action-r104-refund-open-2",
            },
            "idempotency_key": "action-wrap-r104-refund-open-2",
        },
    )
    assert second.status_code in (201, 409)
    refunds = client.get("/api/refunds?return_id=R104", headers=headers).json()["items"]
    assert len([r for r in refunds if r["refund_status"] in ("requested", "approved")]) == 1  # never two open requests


def test_agent_tool_submit_refund(populated_db) -> None:
    prepare_for_submission(populated_db, "R101")
    _seed(populated_db, "act_agent_user", UserRole.RETURNS_ANALYST)
    set_agent_context(
        populated_db,
        CurrentUser(user_id=1, username="act_agent_user", role=UserRole.RETURNS_ANALYST),
    )
    try:
        raw = submit_refund_request.invoke(
            {
                "return_id": "R101",
                "refund_amount_paise": 50000,
                "idempotency_key": "tool-refund-r101-a",
            }
        )
    finally:
        clear_agent_context()
    data = json.loads(raw)
    assert data.get("error") is None, data
    assert data["approval_required"] is False  # the supervisor decides on the refund itself
    assert data["execution_status"] == "succeeded"
