"""Document preview API."""

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import UserRole
from app.models.tables import User
from app.security.passwords import hash_password

client = TestClient(app)


def _login(populated_db, username: str) -> str:
    populated_db.add(
        User(
            username=username,
            password_hash=hash_password("doc-test-pass"),
            role=UserRole.RETURNS_ANALYST.value,
            active=True,
        )
    )
    populated_db.commit()
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "doc-test-pass"},
    )
    return response.json()["access_token"]


def test_document_preview_returns_text(populated_db) -> None:
    from app.documents.loader import load_document_metadata_from_manifest
    from sqlalchemy import select

    from app.models.tables import DocumentMetadata

    report = load_document_metadata_from_manifest(populated_db)
    assert report.ok, report

    token = _login(populated_db, "doc_preview_user")
    row = populated_db.execute(select(DocumentMetadata).limit(1)).scalar_one()
    preview = client.get(
        f"/api/documents/{row.document_id}/preview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["document_id"] == row.document_id
    assert body["filename"] == row.filename
    assert body["full_text"]
    assert body["segments"]
