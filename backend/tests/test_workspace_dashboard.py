"""Workspace dashboard API (persona-scoped)."""

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import UserRole
from app.models.tables import User
from app.security.passwords import hash_password

client = TestClient(app)


def _seed_user(db_session, username: str, role: UserRole, password: str = "dash-pass-1") -> None:
    db_session.add(
        User(
            username=username,
            password_hash=hash_password(password),
            role=role.value,
            active=True,
        )
    )
    db_session.commit()


def _headers(username: str, password: str = "dash-pass-1") -> dict[str, str]:
    token = client.post("/api/auth/login", json={"username": username, "password": password}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_workspace_dashboard_analyst(populated_db) -> None:
    _seed_user(populated_db, "dash_analyst", UserRole.RETURNS_ANALYST)
    res = client.get("/api/dashboard/workspace", headers=_headers("dash_analyst"))
    assert res.status_code == 200
    body = res.json()
    assert body["persona"] == "returns_analyst"
    assert "queue_total" in body["kpis"]
    assert "ready_for_supervisor" in body["kpis"]
    assert "needs_investigation" in body["kpis"]
    keys = {s["key"] for s in body["sections"]}
    assert "work_queue" in keys
    items = [i for s in body["sections"] if s["key"] == "work_queue" for i in s["items"]]
    assert body["kpis"]["your_move"] == len([i for i in items if i["your_move"]])
    if items:
        assert "last_activity_at" in items[0] or items[0].get("last_update_summary") is None


def test_workspace_dashboard_warehouse(populated_db) -> None:
    _seed_user(populated_db, "dash_wh", UserRole.WAREHOUSE_MANAGER)
    res = client.get("/api/dashboard/workspace", headers=_headers("dash_wh"))
    assert res.status_code == 200
    body = res.json()
    assert body["persona"] == "warehouse_manager"
    assert body["kpis"]["queue_total"] >= 0
    assert "awaiting_receipt" in body["kpis"]
    keys = {s["key"] for s in body["sections"]}
    assert "warehouse_handoffs" in keys


def test_workspace_dashboard_supervisor(populated_db) -> None:
    _seed_user(populated_db, "dash_sup", UserRole.RETURNS_SUPERVISOR)
    res = client.get("/api/dashboard/workspace", headers=_headers("dash_sup"))
    assert res.status_code == 200
    body = res.json()
    assert body["persona"] == "returns_supervisor"
    assert "queue_total" in body["kpis"]
    assert "queue_shown" in body["kpis"]
    assert "pending_refunds" in body["kpis"]
    assert body["kpis"]["queue_shown"] <= 50
    keys = {s["key"] for s in body["sections"]}
    assert "approval_queue" in keys
    approval = [i for s in body["sections"] if s["key"] == "approval_queue" for i in s["items"]]
    assert len(approval) <= 50
