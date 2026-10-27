"""Dashboard queue ordering when another persona hands off work."""

from __future__ import annotations

import itertools

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.models.enums import UserRole
from app.models.tables import User
from app.security.passwords import hash_password
from app.investigation.investigation import run_investigation

client = TestClient(app)
_counter = itertools.count(1)


def _personas(db) -> dict[str, dict[str, str]]:
    heads = {}
    for name, role in (
        ("analyst", UserRole.RETURNS_ANALYST),
        ("warehouse", UserRole.WAREHOUSE_MANAGER),
    ):
        username = f"qh_{name}"
        db.add(User(username=username, password_hash=hash_password("qh-pass-1"), role=role.value, active=True))
        db.commit()
        token = client.post("/api/auth/login", json={"username": username, "password": "qh-pass-1"}).json()[
            "access_token"
        ]
        heads[name] = {"Authorization": f"Bearer {token}"}
    return heads


def _pick_clean_return(db) -> str:
    rows = db.execute(
        text(
            """SELECT r.return_id FROM returns r
                WHERE r.return_status IN ('received') AND r.return_id > 'R115'
                AND NOT EXISTS (SELECT 1 FROM investigation_cases k WHERE k.return_id = r.return_id)
                ORDER BY r.return_id LIMIT 50"""
        )
    ).all()
    for row in rows:
        report = run_investigation(db, row[0])
        if report and report.f3_policy.within_return_window is True:
            return row[0]
    raise AssertionError("no clean return for handoff test")


def _section_items(body: dict, key: str) -> list[dict]:
    for section in body["sections"]:
        if section["key"] == key:
            return section["items"]
    return []


def test_analyst_case_surfaces_first_on_warehouse_dashboard(populated_db) -> None:
    db = populated_db
    p = _personas(db)
    rid = _pick_clean_return(db)

    assert client.post("/api/cases", headers=p["analyst"], json={"return_id": rid, "issue_type": "general", "priority": "medium"}).status_code == 201

    wh = client.get("/api/dashboard/workspace", headers=p["warehouse"]).json()
    handoffs = _section_items(wh, "warehouse_handoffs")
    assert handoffs, "warehouse queue should list the new handoff"
    assert handoffs[0]["return_id"] == rid
    assert handoffs[0].get("handoff_from_other") is True
    assert handoffs[0].get("last_update_summary")

    recent = _section_items(wh, "recent_updates")
    assert recent and recent[0]["return_id"] == rid
    assert recent[0].get("handoff_from_other") is True
    assert recent[0].get("last_update_actor") == "returns_analyst"
