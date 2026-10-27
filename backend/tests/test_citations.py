from app.agents.citations import build_citations, strip_legacy_sources_block


def test_build_citations_and_append_links() -> None:
    evidence = {
        "structured": [
            {
                "table_name": "returns",
                "title": "Return · R102",
                "rows": [{"return_id": "R102"}],
                "record": {"return_id": "R102"},
            }
        ],
        "documents": [
            {
                "document_id": 9,
                "filename": "policy.pdf",
                "file_path": "data/x.pdf",
                "passage": "30 day window",
                "page": 2,
                "file_kind": "pdf",
            }
        ],
    }
    cites = build_citations(evidence)
    assert len(cites) == 2
    assert cites[0]["path"].startswith("/workspace/data?")
    assert "doc=9" in cites[1]["path"]
    assert "page=2" in cites[1]["path"]
    out = strip_legacy_sources_block("Answer text.\n\n**Sources**\n- x")
    assert out == "Answer text."
