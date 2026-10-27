"""Investigation attaches unstructured document sources for all personas."""

import json

from app.agents.context import clear_agent_context, set_agent_context
from app.agents.document_citations import parse_document_hits
from app.agents.investigation_documents import gather_investigation_document_sources
from app.models.enums import UserRole
from app.security.deps import CurrentUser
from app.tools.investigation_tools import run_return_investigation


def test_gather_investigation_document_sources_includes_policy(populated_db) -> None:
    sources = gather_investigation_document_sources(populated_db, "R102")
    assert isinstance(sources, list)
    if sources:
        assert sources[0].get("document_id")
        assert sources[0].get("filename")


def test_run_return_investigation_json_includes_document_sources(populated_db) -> None:
    set_agent_context(
        populated_db,
        CurrentUser(user_id=1, username="analyst", role=UserRole.RETURNS_ANALYST),
    )
    try:
        raw = run_return_investigation.invoke({"return_id": "R102"})
    finally:
        clear_agent_context()
    data = json.loads(raw)
    assert data.get("truncated") is not True
    assert "f4_outcome" in data
    assert "document_source_count" in data
