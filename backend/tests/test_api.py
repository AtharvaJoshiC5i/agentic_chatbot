"""Phase 6 REST API tests."""

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


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_and_get_return(populated_db) -> None:
    _seed_user(populated_db, "analyst", UserRole.RETURNS_ANALYST)
    login = client.post("/api/auth/login", json={"username": "analyst", "password": "test-password-1"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = client.get("/api/returns/R102", headers=_auth_header(token))
    assert response.status_code == 200
    body = response.json()
    assert body["return_id"] == "R102"
    assert body["product"]["product_name"]


def test_r102_timeline_ordered(populated_db) -> None:
    _seed_user(populated_db, "reader", UserRole.RETURNS_ANALYST)
    token = client.post("/api/auth/login", json={"username": "reader", "password": "test-password-1"}).json()[
        "access_token"
    ]
    events = client.get("/api/returns/R102/timeline", headers=_auth_header(token)).json()
    assert len(events) >= 3
    timestamps = [event["event_timestamp"] for event in events]
    assert timestamps == sorted(timestamps)


def test_r106_duplicate_refund_blocked(populated_db) -> None:
    _seed_user(populated_db, "supervisor", UserRole.RETURNS_SUPERVISOR)
    token = client.post(
        "/api/auth/login",
        json={"username": "supervisor", "password": "test-password-1"},
    ).json()["access_token"]
    headers = _auth_header(token)

    response = client.post(
        "/api/refunds/requests",
        headers=headers,
        json={
            "return_id": "R106",
            "refund_amount_paise": 1000,
            "idempotency_key": "test-r106-duplicate-attempt",
        },
    )
    assert response.status_code == 409


def test_create_case_and_dashboard(populated_db) -> None:
    _seed_user(populated_db, "analyst2", UserRole.RETURNS_ANALYST)
    analyst_token = client.post(
        "/api/auth/login",
        json={"username": "analyst2", "password": "test-password-1"},
    ).json()["access_token"]

    create = client.post(
        "/api/cases",
        headers=_auth_header(analyst_token),
        json={"return_id": "R101", "issue_type": "general", "priority": "medium"},
    )
    assert create.status_code == 201
    case_id = create.json()["case_id"]
    assert create.json()["assigned_to"] == "warehouse_mgr"
    assert create.json()["case_status"] == "assigned"

    dashboard = client.get("/api/dashboard/summary", headers=_auth_header(analyst_token))
    assert dashboard.status_code == 200
    assert dashboard.json()["total_returns"] == 500

    _seed_user(populated_db, "super2", UserRole.RETURNS_SUPERVISOR)
    supervisor_token = client.post(
        "/api/auth/login",
        json={"username": "super2", "password": "test-password-1"},
    ).json()["access_token"]
    assign = client.post(
        f"/api/cases/{case_id}/assign",
        headers=_auth_header(supervisor_token),
        json={"assigned_to": "analyst_07"},
    )
    assert assign.status_code == 200
    assert assign.json()["assigned_to"] == "analyst_07"


def test_unauthorized_without_token() -> None:
    assert client.get("/api/returns").status_code == 401
