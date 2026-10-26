"""End-to-end persona workflow: analyst -> warehouse -> analyst -> supervisor -> analyst -> customer.

Each step is driven through the HTTP API as the persona who owns it, and every hand-off is asserted from the
database or from the *next* persona's own queue, so a change one persona makes must be visible to the next.
"""

from __future__ import annotations

import itertools

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.models.enums import UserRole
from app.models.tables import User
from app.security.passwords import hash_password

client = TestClient(app)
_counter = itertools.count(1)

ROLES = {
    "analyst": UserRole.RETURNS_ANALYST,
    "warehouse": UserRole.WAREHOUSE_MANAGER,
    "supervisor": UserRole.RETURNS_SUPERVISOR,
}


def _personas(db) -> dict[str, dict[str, str]]:
    heads = {}
    for name, role in ROLES.items():
        username = f"wf_{name}"
        db.add(User(username=username, password_hash=hash_password("wf-pass-1"), role=role.value, active=True))
        db.commit()
        token = client.post("/api/auth/login", json={"username": username, "password": "wf-pass-1"}).json()["access_token"]
        heads[name] = {"Authorization": f"Bearer {token}"}
    return heads


def _pick(db, resolution: str, statuses: tuple[str, ...]) -> str:
    marks = ",".join(f"'{s}'" for s in statuses)
    row = db.execute(
        text(
            f"""SELECT r.return_id FROM returns r
                WHERE r.requested_resolution = :res AND r.return_status IN ({marks}) AND r.return_id > 'R115'
                AND NOT EXISTS (SELECT 1 FROM inspections i WHERE i.return_id = r.return_id)
                AND NOT EXISTS (SELECT 1 FROM refunds f WHERE f.return_id = r.return_id)
                AND NOT EXISTS (SELECT 1 FROM investigation_cases k WHERE k.return_id = r.return_id)
                AND NOT EXISTS (SELECT 1 FROM replacement_requests p WHERE p.return_id = r.return_id)
                ORDER BY r.return_id LIMIT 1"""
        ),
        {"res": resolution},
    ).first()
    assert row is not None, f"no clean {resolution} return in the dataset"
    return row[0]


def _price(db, return_id: str) -> int:
    return db.execute(
        text("SELECT oi.unit_price FROM returns r JOIN order_items oi USING(order_item_id) WHERE r.return_id = :r"),
        {"r": return_id},
    ).scalar_one()


def _row(db, sql: str, **params):
    db.expire_all()
    return db.execute(text(sql), params).first()


def _queue_ids(headers: dict[str, str]) -> dict[str, str]:
    body = client.get("/api/dashboard/workspace", headers=headers).json()
    return {item["return_id"]: item.get("workflow_stage") for section in body["sections"] for item in section["items"]}


def _hand_to_warehouse_and_back(db, p, rid: str, *, feasible: bool = True, notes: str | None = None) -> None:
    """Analyst opens the case; warehouse receives, inspects and gives a verdict."""
    assert client.post("/api/cases", headers=p["analyst"], json={"return_id": rid, "issue_type": "general", "priority": "medium"}).status_code == 201
    assert _row(db, "SELECT return_status FROM returns WHERE return_id=:r", r=rid)[0] in ("investigating", "requested", "approved", "pickup_scheduled", "in_transit")
    assert _queue_ids(p["warehouse"]).get(rid) in ("receive", "inspect")  # the warehouse sees it

    assert client.post(f"/api/returns/{rid}/receive", headers=p["warehouse"]).status_code == 200
    ins = client.post(
        f"/api/returns/{rid}/inspections",
        headers=p["warehouse"],
        json={"product_condition": "damaged", "accessories_complete": True, "defect_verified": feasible, "inspection_result": "pass" if feasible else "fail", "inspector_notes": "bench test"},
    )
    assert ins.status_code == 201, ins.text
    case = _row(db, "SELECT case_status, assigned_to FROM investigation_cases WHERE return_id=:r ORDER BY case_id DESC", r=rid)
    assert case[0] == "in_progress" and case[1] == "wf_warehouse"  # warehouse picked the case up
    assert _queue_ids(p["warehouse"]).get(rid) == "verdict"

    verdict = client.post(
        f"/api/returns/{rid}/verdict",
        headers=p["warehouse"],
        json={"feasible": feasible, "recommendation": "proceed" if feasible else "decline", "notes": notes},
    )
    assert verdict.status_code == 201, verdict.text
    assert _row(db, "SELECT case_status FROM investigation_cases WHERE return_id=:r ORDER BY case_id DESC", r=rid)[0] == "ready_for_review"
    assert rid not in _queue_ids(p["warehouse"])  # handed back


def test_refund_approved_path(populated_db) -> None:
    db, p = populated_db, _personas(populated_db)
    rid = _pick(db, "refund", ("received",))
    amount = _price(db, rid)

    # Nothing can be submitted before the analyst opens a case and the warehouse gives a verdict.
    blocked = client.post("/api/refunds/requests", headers=p["analyst"], json={"return_id": rid, "refund_amount_paise": amount, "idempotency_key": "wf-early-0001"})
    assert blocked.status_code == 409 and "case" in blocked.json()["detail"].lower()

    assert client.post("/api/cases", headers=p["analyst"], json={"return_id": rid, "issue_type": "general", "priority": "medium"}).status_code == 201
    still = client.post("/api/refunds/requests", headers=p["analyst"], json={"return_id": rid, "refund_amount_paise": amount, "idempotency_key": "wf-early-0002"})
    assert still.status_code == 409 and "warehouse" in still.json()["detail"].lower()
    db.execute(text("DELETE FROM investigation_cases WHERE return_id=:r"), {"r": rid})
    db.execute(text("UPDATE returns SET return_status='received' WHERE return_id=:r"), {"r": rid})
    db.commit()

    _hand_to_warehouse_and_back(db, p, rid)
    assert _queue_ids(p["analyst"]).get(rid) == "submit_refund"  # the analyst is told it is their move

    request = client.post("/api/refunds/requests", headers=p["analyst"], json={"return_id": rid, "refund_amount_paise": amount, "idempotency_key": "wf-approve-0001"})
    assert request.status_code == 201, request.text
    refund_id = request.json()["refund_id"]
    assert _row(db, "SELECT case_status FROM investigation_cases WHERE return_id=:r ORDER BY case_id DESC", r=rid)[0] == "pending_approval"
    assert _queue_ids(p["analyst"]).get(rid) == "await_supervisor"
    assert any(i["return_id"] == rid for i in client.get("/api/approvals", headers=p["supervisor"]).json()["refunds"])

    # A second open request for the same return is refused.
    dup = client.post("/api/refunds/requests", headers=p["analyst"], json={"return_id": rid, "refund_amount_paise": amount, "idempotency_key": "wf-approve-0002"})
    assert dup.status_code == 409

    # Only the supervisor decides; one approval pays the refund out.
    assert client.post(f"/api/refunds/{refund_id}/approve", headers=p["analyst"], json={"approve": True}).status_code == 403
    done = client.post(f"/api/refunds/{refund_id}/approve", headers=p["supervisor"], json={"approve": True})
    assert done.status_code == 200 and done.json()["refund_status"] == "completed"
    assert _row(db, "SELECT return_status FROM returns WHERE return_id=:r", r=rid)[0] == "resolved"
    assert _row(db, "SELECT case_status FROM investigation_cases WHERE return_id=:r ORDER BY case_id DESC", r=rid)[0] == "resolved"
    assert _row(db, "SELECT decided_by FROM refunds WHERE refund_id=:i", i=refund_id)[0] == "wf_supervisor"

    # The decision comes back to the analyst as a drafted customer email.
    assert _queue_ids(p["analyst"]).get(rid) == "customer_follow_up"
    drafts = client.get(f"/api/notifications?status=draft&return_id={rid}", headers=p["analyst"]).json()["items"]
    assert len(drafts) == 1 and drafts[0]["kind"] == "refund_approved" and "approved" in drafts[0]["body"]
    sent = client.post(f"/api/notifications/{drafts[0]['notification_id']}/send", headers=p["analyst"], json={})
    assert sent.status_code == 200 and sent.json()["status"] == "sent"
    assert _row(db, "SELECT return_status FROM returns WHERE return_id=:r", r=rid)[0] == "closed"
    assert _row(db, "SELECT case_status FROM investigation_cases WHERE return_id=:r ORDER BY case_id DESC", r=rid)[0] == "closed"
    assert rid not in _queue_ids(p["analyst"])  # finished


def test_refund_rejected_path_needs_a_reason_and_reaches_the_analyst(populated_db) -> None:
    db, p = populated_db, _personas(populated_db)
    rid = _pick(db, "refund", ("received",))
    _hand_to_warehouse_and_back(db, p, rid)
    refund_id = client.post("/api/refunds/requests", headers=p["analyst"], json={"return_id": rid, "refund_amount_paise": _price(db, rid), "idempotency_key": "wf-reject-0001"}).json()["refund_id"]

    assert client.post(f"/api/refunds/{refund_id}/approve", headers=p["supervisor"], json={"approve": False}).status_code == 400
    rejected = client.post(f"/api/refunds/{refund_id}/approve", headers=p["supervisor"], json={"approve": False, "reason": "Damage is consistent with misuse."})
    assert rejected.status_code == 200 and rejected.json()["refund_status"] == "cancelled"
    assert _row(db, "SELECT return_status FROM returns WHERE return_id=:r", r=rid)[0] == "rejected"
    assert _queue_ids(p["analyst"]).get(rid) == "customer_follow_up"
    draft = client.get(f"/api/notifications?status=draft&return_id={rid}", headers=p["analyst"]).json()["items"][0]
    assert draft["kind"] == "refund_rejected" and "misuse" in draft["body"]
    assert client.post(f"/api/notifications/{draft['notification_id']}/send", headers=p["analyst"], json={"subject": "Update on your return"}).status_code == 200
    assert _row(db, "SELECT return_status FROM returns WHERE return_id=:r", r=rid)[0] == "closed"


def test_warehouse_decline_stops_the_analyst_submitting(populated_db) -> None:
    db, p = populated_db, _personas(populated_db)
    rid = _pick(db, "refund", ("received",))
    assert client.post("/api/cases", headers=p["analyst"], json={"return_id": rid, "issue_type": "general", "priority": "medium"}).status_code == 201
    client.post(f"/api/returns/{rid}/inspections", headers=p["warehouse"], json={"product_condition": "open_box", "accessories_complete": True, "defect_verified": False, "inspection_result": "fail", "inspector_notes": "Fault not reproduced"})
    assert client.post(f"/api/returns/{rid}/verdict", headers=p["warehouse"], json={"feasible": False, "recommendation": "decline"}).status_code == 400  # needs a reason
    assert client.post(f"/api/returns/{rid}/verdict", headers=p["warehouse"], json={"feasible": False, "recommendation": "decline", "notes": "Fault could not be reproduced in 60 minutes of testing."}).status_code == 201

    assert _queue_ids(p["analyst"]).get(rid) == "decline_request"
    blocked = client.post("/api/refunds/requests", headers=p["analyst"], json={"return_id": rid, "refund_amount_paise": _price(db, rid), "idempotency_key": "wf-decl-0001"})
    assert blocked.status_code == 409 and "cannot be performed" in blocked.json()["detail"]

    assert client.post(f"/api/returns/{rid}/decline", headers=p["warehouse"], json={"reason": "x"}).status_code == 403
    assert client.post(f"/api/returns/{rid}/decline", headers=p["analyst"], json={"reason": "  "}).status_code in (400, 409)
    ok = client.post(f"/api/returns/{rid}/decline", headers=p["analyst"], json={"reason": "Warehouse could not reproduce the fault."})
    assert ok.status_code == 200 and ok.json()["return_status"] == "rejected"
    draft = client.get(f"/api/notifications?status=draft&return_id={rid}", headers=p["analyst"]).json()["items"][0]
    assert draft["kind"] == "declined" and "could not reproduce" in draft["body"]
    assert client.post(f"/api/notifications/{draft['notification_id']}/send", headers=p["analyst"], json={}).status_code == 200
    assert _row(db, "SELECT return_status FROM returns WHERE return_id=:r", r=rid)[0] == "closed"


def test_replacement_path_checks_stock_and_decrements_it(populated_db) -> None:
    db, p = populated_db, _personas(populated_db)
    rid = _pick(db, "replacement", ("requested", "approved", "pickup_scheduled", "in_transit", "received"))
    product_id = _row(db, "SELECT oi.product_id FROM returns r JOIN order_items oi USING(order_item_id) WHERE r.return_id=:r", r=rid)[0]

    # No stock: the warehouse cannot call the replacement feasible.
    db.execute(text("UPDATE products SET stock_on_hand=0 WHERE product_id=:p"), {"p": product_id})
    db.commit()
    assert client.post("/api/cases", headers=p["analyst"], json={"return_id": rid, "issue_type": "general", "priority": "medium"}).status_code == 201
    client.post(f"/api/returns/{rid}/receive", headers=p["warehouse"])
    client.post(f"/api/returns/{rid}/inspections", headers=p["warehouse"], json={"product_condition": "damaged", "accessories_complete": True, "defect_verified": True, "inspection_result": "pass"})
    no_stock = client.post(f"/api/returns/{rid}/verdict", headers=p["warehouse"], json={"feasible": True, "recommendation": "proceed"})
    assert no_stock.status_code == 409 and "stock" in no_stock.json()["detail"].lower()

    db.execute(text("UPDATE products SET stock_on_hand=3 WHERE product_id=:p"), {"p": product_id})
    db.commit()
    assert client.post(f"/api/returns/{rid}/verdict", headers=p["warehouse"], json={"feasible": True, "recommendation": "proceed"}).status_code == 201
    assert _queue_ids(p["analyst"]).get(rid) == "submit_replacement"

    wrong = client.post("/api/refunds/requests", headers=p["analyst"], json={"return_id": rid, "refund_amount_paise": 1000, "idempotency_key": "wf-repl-0001"})
    assert wrong.status_code == 409 and "replacement" in wrong.json()["detail"]
    req = client.post("/api/replacements/requests", headers=p["analyst"], json={"return_id": rid})
    assert req.status_code == 201, req.text
    rep_id = req.json()["replacement_id"]
    assert any(i["return_id"] == rid for i in client.get("/api/approvals", headers=p["supervisor"]).json()["replacements"])

    assert client.post(f"/api/replacements/{rep_id}/decision", headers=p["analyst"], json={"approve": True}).status_code == 403
    decided = client.post(f"/api/replacements/{rep_id}/decision", headers=p["supervisor"], json={"approve": True})
    assert decided.status_code == 200 and decided.json()["status"] == "approved" and decided.json()["replacement_order_id"]
    assert _row(db, "SELECT stock_on_hand FROM products WHERE product_id=:p", p=product_id)[0] == 2
    assert _row(db, "SELECT return_status FROM returns WHERE return_id=:r", r=rid)[0] == "resolved"
    assert _queue_ids(p["analyst"]).get(rid) == "customer_follow_up"
    draft = client.get(f"/api/notifications?status=draft&return_id={rid}", headers=p["analyst"]).json()["items"][0]
    assert draft["kind"] == "replacement_approved"
    assert client.post(f"/api/notifications/{draft['notification_id']}/send", headers=p["analyst"], json={}).status_code == 200
    assert _row(db, "SELECT return_status FROM returns WHERE return_id=:r", r=rid)[0] == "closed"


def test_each_persona_only_does_their_own_step(populated_db) -> None:
    db, p = populated_db, _personas(populated_db)
    rid = _pick(db, "refund", ("received",))
    assert client.post("/api/cases", headers=p["warehouse"], json={"return_id": rid, "issue_type": "general", "priority": "low"}).status_code == 403
    assert client.post("/api/cases", headers=p["analyst"], json={"return_id": rid, "issue_type": "general", "priority": "low"}).status_code == 201
    assert client.post(f"/api/returns/{rid}/verdict", headers=p["analyst"], json={"feasible": True, "recommendation": "proceed"}).status_code == 403
    assert client.post(f"/api/returns/{rid}/inspections", headers=p["analyst"], json={"product_condition": "new", "inspection_result": "pass"}).status_code == 403
    assert client.post("/api/refunds/requests", headers=p["warehouse"], json={"return_id": rid, "refund_amount_paise": 1000, "idempotency_key": "wf-role-0001"}).status_code == 403
    assert client.get("/api/approvals", headers=p["analyst"]).status_code == 403
    assert client.get("/api/approvals", headers=p["supervisor"]).status_code == 200


def test_analyst_queue_is_not_capped_by_recency(populated_db) -> None:
    """The earlier queue took the 40 newest returns first, so older in-flight work vanished."""
    db, p = populated_db, _personas(populated_db)
    rid = _pick(db, "refund", ("received",))
    db.execute(text("UPDATE returns SET request_date='2020-01-01 00:00:00' WHERE return_id=:r"), {"r": rid})
    db.commit()
    _hand_to_warehouse_and_back(db, p, rid)
    stages = _queue_ids(p["analyst"])
    assert stages.get(rid) == "submit_refund"
    body = client.get("/api/dashboard/workspace", headers=p["analyst"]).json()
    assert body["kpis"]["your_move"] >= 1
