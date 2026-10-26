"""Phase 13 monitoring and alerts tests."""

from datetime import timedelta

from fastapi.testclient import TestClient

from app.database.base import utc_now
from app.main import app
from app.models.enums import AlertType, UserRole
from sqlalchemy import select

from app.models.tables import InvestigationCase, User
from app.security.passwords import hash_password
from app.services.monitoring import collect_findings, run_monitoring_checks

client = TestClient(app)


def _seed(db, username: str, role: UserRole) -> None:
    db.add(
        User(
            username=username,
            password_hash=hash_password("mon-pass"),
            role=role.value,
            active=True,
        )
    )
    db.commit()


def _auth(username: str) -> dict[str, str]:
    token = client.post("/api/auth/login", json={"username": username, "password": "mon-pass"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_r113_awaiting_inspection_finding(populated_db) -> None:
    findings = collect_findings(populated_db)
    assert any(
        f.alert_type == AlertType.AWAITING_INSPECTION and f.related_id == "R113" for f in findings
    )


def test_monitoring_dedup_and_resolve(populated_db) -> None:
    first = run_monitoring_checks(populated_db, commit=True)
    second = run_monitoring_checks(populated_db, commit=True)
    assert second.alerts_created == 0
    assert second.open_alerts == first.open_alerts


def test_overdue_investigation_alert(populated_db) -> None:
    row = populated_db.execute(select(InvestigationCase).limit(1)).scalar_one_or_none()
    assert row is not None
    row.due_date = utc_now() - timedelta(days=3)
    populated_db.commit()

    result = run_monitoring_checks(populated_db, commit=True)
    assert result.findings_count >= 1
    assert AlertType.OVERDUE_INVESTIGATION.value in result.by_type


def test_monitoring_api(populated_db) -> None:
    _seed(populated_db, "mon_super", UserRole.RETURNS_SUPERVISOR)
    headers = _auth("mon_super")
    run = client.post("/api/monitoring/run", headers=headers)
    assert run.status_code == 200
    summary = client.get("/api/monitoring/summary", headers=headers)
    assert summary.status_code == 200
    assert "open_alerts" in summary.json()
