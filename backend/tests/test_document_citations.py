"""Document citation parsing from RAG tool output."""

from app.agents.document_citations import (
    aggregate_document_sources,
    enrich_tool_events_with_documents,
    parse_document_hits,
)


def test_parse_search_tool_hits() -> None:
    raw = """[
      {"document_id": 1, "filename": "inspection_R102.pdf", "file_path": "data/x.pdf",
       "page_or_section": "Page 1", "passage": "Serial mismatch noted.", "relevance_score": 0.91}
    ]"""
    hits = parse_document_hits("search_inspection_reports", raw)
    assert len(hits) == 1
    assert hits[0]["file_kind"] == "pdf"
    assert hits[0]["passage"] == "Serial mismatch noted."


def test_enrich_and_aggregate_tool_events() -> None:
    events = [
        {
            "tool": "search_customer_complaints",
            "args": {"query": "serial"},
            "result_preview": (
                '[{"document_id": 2, "filename": "complaint.docx", "file_path": "data/c.docx", '
                '"page_or_section": null, "passage": "Left side no sound.", "relevance_score": 0.8}]'
            ),
        }
    ]
    enrich_tool_events_with_documents(events)
    assert events[0]["document_hits"][0]["file_kind"] == "docx"
    sources = aggregate_document_sources(events)
    assert len(sources) == 1
