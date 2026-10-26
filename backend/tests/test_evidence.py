"""Supporting evidence parsing."""

from app.agents.evidence import build_supporting_evidence, parse_structured_evidence


def test_parse_return_details_evidence() -> None:
    preview = '{"return_id":"R102","return_status":"under_review","return_reason":"defective"}'
    items = parse_structured_evidence("get_return_details", preview)
    assert len(items) == 1
    assert items[0]["table_name"] == "returns"
    assert "R102" in items[0]["title"]
    assert items[0]["rows"][0]["return_id"] == "R102"


def test_build_supporting_evidence_merges_documents() -> None:
    events = [
        {
            "tool": "get_return_details",
            "result_preview": '{"return_id":"R102","return_status":"open"}',
        },
        {
            "tool": "search_inspection_reports",
            "result_preview": (
                '[{"document_id": 1, "filename": "a.pdf", "file_path": "data/a.pdf", '
                '"passage": "Serial mismatch", "relevance_score": 0.9}]'
            ),
            "document_hits": [
                {
                    "document_id": 1,
                    "filename": "a.pdf",
                    "file_path": "data/a.pdf",
                    "passage": "Serial mismatch",
                    "file_kind": "pdf",
                }
            ],
        },
    ]
    bundle = build_supporting_evidence(events)
    assert len(bundle["structured"]) == 1
    assert len(bundle["documents"]) == 1
