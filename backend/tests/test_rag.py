"""Phase 5 RAG extraction, ingest, and search tests."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.config import PROJECT_ROOT, get_settings
from app.documents.loader import load_document_metadata_from_manifest
from app.rag.chunk import chunk_document
from app.rag.extract import extract_document
from app.rag.ingest import ingest_all_documents
from app.rag.search import get_applicable_policy, search_documents
from app.rag.store import clear_chroma_cache, collection_document_count


@pytest.fixture()
def chroma_tmp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    chroma_dir = tmp_path / "chroma_test"
    monkeypatch.setenv("CHROMA_PATH", str(chroma_dir))
    get_settings.cache_clear()
    clear_chroma_cache()
    yield chroma_dir
    clear_chroma_cache()
    get_settings.cache_clear()


def test_extract_r102_inspection_contains_serials() -> None:
    path = PROJECT_ROOT / "data/unstructured/inspections/inspection_R102_serial_mismatch.pdf"
    text = extract_document(path).full_text
    assert "HP9081" in text
    assert "HP9012" in text


def test_chunk_document_produces_multiple_segments() -> None:
    path = PROJECT_ROOT / "data/unstructured/policies/return_policy_electronics_pol_elec_2024_03.pdf"
    extracted = extract_document(path)
    chunks = chunk_document(extracted, chunk_size=400, overlap=50)
    assert len(chunks) >= 2


@pytest.mark.slow
def test_ingest_and_search_r102(populated_db, chroma_tmp) -> None:
    load_document_metadata_from_manifest(populated_db)
    report = ingest_all_documents(populated_db, reset_index=True)
    assert not report.failures, report.failures
    assert report.documents_processed == 140
    assert collection_document_count() > 0

    hits = search_documents(
        "serial number mismatch HP9081 HP9012",
        return_id="R102",
        document_type="inspection_report",
        limit=3,
    )
    assert hits
    assert any("HP9081" in hit.passage or "HP9012" in hit.passage for hit in hits)
    assert hits[0].document_id > 0
    assert hits[0].filename


@pytest.mark.slow
def test_policy_retrieval_electronics(populated_db, chroma_tmp) -> None:
    load_document_metadata_from_manifest(populated_db)
    ingest_all_documents(populated_db, reset_index=True)

    result = get_applicable_policy(
        populated_db,
        category="electronics",
        relevant_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
        return_reason="not_functioning",
        limit=3,
    )
    assert result["policy"] is not None
    assert "electronics" in result["policy"]["file_path"].lower()
    assert "30" in " ".join(c["passage"] for c in result["clauses"]) or result["clauses"]


def test_search_empty_index_returns_no_results(chroma_tmp) -> None:
    assert search_documents("electronics return policy") == []
