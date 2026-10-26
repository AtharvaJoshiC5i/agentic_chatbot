"""Phase 11 recovery optimizer tests."""

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import RecoveryMethod, UserRole
from app.models.tables import User
from app.security.passwords import hash_password
from app.services.recovery_optimizer import optimize_recovery

client = TestClient(app)


def _seed(db, username: str, role: UserRole) -> None:
    db.add(
        User(
            username=username,
            password_hash=hash_password("recovery-pass"),
            role=role.value,
            active=True,
        )
    )
    db.commit()


def _auth(username: str) -> dict[str, str]:
    token = client.post(
        "/api/auth/login",
        json={"username": username, "password": "recovery-pass"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_r108_recommends_repair_resell(populated_db) -> None:
    recommendation = optimize_recovery(populated_db, "R108")
    assert recommendation.recommended_method == RecoveryMethod.REPAIR_RESELL.value
    assert recommendation.recommended_option_id is not None
    assert recommendation.unsafe_product is False
    top = next(row for row in recommendation.ranked_options if row.rank == 1)
    assert top.expected_net_recovery_paise == max(
        row.expected_net_recovery_paise for row in recommendation.ranked_options if row.eligible
    )


def test_r115_blocks_resale_paths(populated_db) -> None:
    recommendation = optimize_recovery(populated_db, "R115")
    assert recommendation.unsafe_product is True
    assert recommendation.recommended_method in {
        RecoveryMethod.DISPOSE.value,
        RecoveryMethod.RECYCLE.value,
        RecoveryMethod.SUPPLIER_RETURN.value,
    }
    for row in recommendation.ranked_options:
        if row.recovery_method in {"resell_new", "open_box_resale", "repair_and_resell", "refurbish_and_resell"}:
            assert row.eligible is False


def test_recovery_recommendation_api(populated_db) -> None:
    _seed(populated_db, "rec_reader", UserRole.WAREHOUSE_MANAGER)
    response = client.get("/api/recovery/returns/R108/recommendation", headers=_auth("rec_reader"))
    assert response.status_code == 200
    body = response.json()
    assert body["recommended_method"] == RecoveryMethod.REPAIR_RESELL.value


def test_create_task_from_recommendation_idempotent(populated_db) -> None:
    _seed(populated_db, "rec_mgr", UserRole.WAREHOUSE_MANAGER)
    headers = _auth("rec_mgr")
    first = client.post(
        "/api/recovery/returns/R108/tasks/from-recommendation",
        headers=headers,
        params={"assigned_to": "warehouse_mgr_01"},
    )
    assert first.status_code == 200
    second = client.post(
        "/api/recovery/returns/R108/tasks/from-recommendation",
        headers=headers,
        params={"assigned_to": "warehouse_mgr_01"},
    )
    assert second.status_code == 200
    assert first.json()["recovery_task_id"] == second.json()["recovery_task_id"]
