"""Phase 9 return_events timeline tests."""

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import IssueType, UserRole
from app.models.tables import ReturnEvent, User
from app.security.passwords import hash_password
from app.services.timeline import build_return_timeline
from sqlalchemy import func, select

client = TestClient(app)


def _seed_user(db_session, username: str, role: UserRole, password: str = "timeline-pass") -> None:
    db_session.add(
        User(
            username=username,
            password_hash=hash_password(password),
            role=role.value,
            active=True,
        )
    )
    db_session.commit()


def _auth(username: str, password: str = "timeline-pass") -> dict[str, str]:
    token = client.post("/api/auth/login", json={"username": username, "password": password}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_timeline_sync_persists_events(populated_db) -> None:
    events = build_return_timeline(populated_db, "R102", sync=True)
    assert len(events) >= 5
    count = populated_db.execute(
        select(func.count()).select_from(ReturnEvent).where(ReturnEvent.return_id == "R102")
    ).scalar_one()
    assert count == len(events)


def test_timeline_sync_is_idempotent(populated_db) -> None:
    first = build_return_timeline(populated_db, "R102", sync=True)
    second = build_return_timeline(populated_db, "R102", sync=True)
    assert len(first) == len(second)
    timestamps = [e["event_timestamp"] for e in second]
    assert timestamps == sorted(timestamps)


def test_timeline_api_r102(populated_db) -> None:
    _seed_user(populated_db, "tl_reader", UserRole.RETURNS_ANALYST)
    response = client.get("/api/returns/R102/timeline", headers=_auth("tl_reader"))
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 3
    types = {row["event_type"] for row in body}
    assert "return_requested" in types
    assert "inspection_completed" in types


def test_create_case_appends_timeline_event(populated_db) -> None:
    _seed_user(populated_db, "tl_analyst", UserRole.RETURNS_ANALYST)
    headers = _auth("tl_analyst")
    before = client.get("/api/returns/R101/timeline", headers=headers).json()

    create = client.post(
        "/api/cases",
        headers=headers,
        json={
            "return_id": "R101",
            "issue_type": IssueType.GENERAL.value,
            "priority": "medium",
        },
    )
    assert create.status_code == 201
    case_id = create.json()["case_id"]

    after = client.get("/api/returns/R101/timeline", headers=headers).json()
    assert len(after) >= len(before) + 1
    assert any(
        row["event_type"] == "investigation_opened" and str(case_id) in row["source_id"]
        for row in after
    )
