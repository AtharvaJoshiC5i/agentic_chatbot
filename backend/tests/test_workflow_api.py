"""Workflow endpoints (Phase 3)."""

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import UserRole
from app.models.tables import User
from app.security.passwords import hash_password

client = TestClient(app)


def _seed_user(db_session, username: str, role: UserRole, password: str = "test-password-1") -> None:
    db_session.add(
        User(
            username=username,
            password_hash=hash_password(password),
            role=role.value,
            active=True,
        )
    )
    db_session.commit()


def _token(username: str, password: str = "test-password-1") -> str:
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_list_refunds_and_actions_without_return_id(populated_db) -> None:
    _seed_user(populated_db, "sup", UserRole.RETURNS_SUPERVISOR)
    headers = {"Authorization": f"Bearer {_token('sup')}"}
    refunds = client.get("/api/refunds?status=requested", headers=headers)
    assert refunds.status_code == 200
    assert "items" in refunds.json()
    actions = client.get("/api/actions?status=pending", headers=headers)
    assert actions.status_code == 200
    assert "items" in actions.json()


def test_approvals_queue(populated_db) -> None:
    _seed_user(populated_db, "sup2", UserRole.RETURNS_SUPERVISOR)
    _seed_user(populated_db, "wh", UserRole.WAREHOUSE_MANAGER)
    sup_headers = {"Authorization": f"Bearer {_token('sup2')}"}
    wh_headers = {"Authorization": f"Bearer {_token('wh')}"}
    denied = client.get("/api/approvals", headers=wh_headers)
    assert denied.status_code == 403
    ok = client.get("/api/approvals", headers=sup_headers)
    assert ok.status_code == 200
    body = ok.json()
    assert "refunds" in body and "actions" in body


def test_record_inspection_moves_status(populated_db) -> None:
    _seed_user(populated_db, "wh2", UserRole.WAREHOUSE_MANAGER)
    headers = {"Authorization": f"Bearer {_token('wh2')}"}
    return_id = "R113"
    before = client.get(f"/api/returns/{return_id}", headers=headers).json()
    assert before["return_status"] == "received"
    payload = {
        "product_condition": "defective",
        "inspection_result": "pass",
        "accessories_complete": True,
        "defect_verified": False,
        "inspector_notes": "Test inspection",
    }
    created = client.post(f"/api/returns/{return_id}/inspections", json=payload, headers=headers)
    assert created.status_code == 201
    after = client.get(f"/api/returns/{return_id}", headers=headers).json()
    # R113 demo path: no analyst case → stays inspecting; with case → investigating
    assert after["return_status"] in ("inspecting", "investigating")

