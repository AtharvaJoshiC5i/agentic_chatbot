"""Document bootstrap API."""

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import UserRole
from app.models.tables import User
from app.security.passwords import hash_password

client = TestClient(app)


def _token(db, role: UserRole = UserRole.RETURNS_SUPERVISOR) -> str:
    db.add(
        User(
            username="doc_boot_user",
            password_hash=hash_password("doc-boot-pass"),
            role=role.value,
            active=True,
        )
    )
    db.commit()
    res = client.post("/api/auth/login", json={"username": "doc_boot_user", "password": "doc-boot-pass"})
    return res.json()["access_token"]


def test_documents_status_requires_auth() -> None:
    assert client.get("/api/data-browser/documents/status").status_code == 401


def test_documents_bootstrap_populated(populated_db, monkeypatch) -> None:
    from app.rag.ingest import IngestReport

    monkeypatch.setattr(
        "app.services.document_bootstrap.ingest_all_documents",
        lambda _s, **kw: IngestReport(documents_processed=1, chunks_indexed=5, failures=[]),
    )
    headers = {"Authorization": f"Bearer {_token(populated_db)}"}
    status = client.get("/api/data-browser/documents/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["return_count"] > 0

    res = client.post("/api/data-browser/documents/bootstrap", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["metadata_count"] > 0
