"""Data browser API (structured tables + documents)."""

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import UserRole
from app.models.tables import User
from app.security.passwords import hash_password

client = TestClient(app)


def _token(db) -> str:
    db.add(
        User(
            username="browser_user",
            password_hash=hash_password("browser-pass"),
            role=UserRole.RETURNS_SUPERVISOR.value,
            active=True,
        )
    )
    db.commit()
    res = client.post("/api/auth/login", json={"username": "browser_user", "password": "browser-pass"})
    return res.json()["access_token"]


def test_data_browser_requires_auth() -> None:
    assert client.get("/api/data-browser/overview").status_code == 401


def test_data_browser_lists_tables_and_documents(populated_db) -> None:
    token = _token(populated_db)
    headers = {"Authorization": f"Bearer {token}"}

    overview = client.get("/api/data-browser/overview", headers=headers)
    assert overview.status_code == 200
    body = overview.json()
    assert body["structured_table_count"] >= 5
    assert body["document_count"] >= 0
    assert body["database_file_exists"] is True
    assert body.get("database_file")

    tables = client.get("/api/data-browser/tables", headers=headers).json()["tables"]
    assert any(t["name"] == "returns" for t in tables)

    rows = client.get("/api/data-browser/tables/returns/rows?limit=5", headers=headers)
    assert rows.status_code == 200
    payload = rows.json()
    assert payload["table_name"] == "returns"
    assert payload["total"] >= 1
    assert "return_id" in payload["columns"]
    sample_rid = payload["rows"][0]["return_id"]
    matched = client.get(
        f"/api/data-browser/tables/returns/rows?col=return_id&val={sample_rid}",
        headers=headers,
    )
    assert matched.status_code == 200
    match_body = matched.json()
    assert match_body["matched"]["column"] == "return_id"
    assert match_body["rows"][0]["return_id"] == sample_rid

    docs = client.get("/api/data-browser/documents?limit=10", headers=headers)
    assert docs.status_code == 200
    doc_body = docs.json()
    assert doc_body["total"] >= 0
    if doc_body["items"]:
        assert doc_body["items"][0]["document_id"] >= 1

    users = client.get("/api/data-browser/tables/users/rows", headers=headers).json()
    if users["rows"]:
        assert "password_hash" not in users["columns"]
