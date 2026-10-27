"""Parse document RAG tool output into structured citations for the UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DOCUMENT_TOOL_NAMES = frozenset(
    {
        "search_return_policy",
        "search_inspection_reports",
        "search_customer_complaints",
        "search_support_communications",
        "search_warranty_documents",
        "search_supplier_reports",
        "search_refurbishment_guidelines",
        "resolve_applicable_policy",
        "run_return_investigation",
    }
)


def _file_kind(filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext or "unknown"


def _normalize_hit(raw: dict[str, Any]) -> dict[str, Any] | None:
    document_id = raw.get("document_id")
    filename = raw.get("filename") or ""
    file_path = raw.get("file_path") or ""
    passage = raw.get("passage") or ""
    if document_id is None or not filename:
        return None
    page_raw = raw.get("page")
    page: int | None = None
    if page_raw is not None:
        try:
            page = int(page_raw)
        except (TypeError, ValueError):
            page = None
    return {
        "document_id": int(document_id),
        "filename": str(filename),
        "file_path": str(file_path),
        "page_or_section": raw.get("page_or_section"),
        "page": page if page and page > 0 else None,
        "passage": str(passage),
        "relevance_score": raw.get("relevance_score"),
        "file_kind": _file_kind(str(filename)),
    }


def parse_document_hits(tool_name: str, content: Any) -> list[dict[str, Any]]:
    if tool_name not in DOCUMENT_TOOL_NAMES:
        return []
    if content is None:
        return []
    text = content if isinstance(content, str) else str(content)
    text = text.strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []

    hits: list[dict[str, Any]] = []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                hit = _normalize_hit(item)
                if hit:
                    hits.append(hit)
    elif isinstance(payload, dict):
        embedded = payload.get("document_sources")
        if isinstance(embedded, list):
            for item in embedded:
                if isinstance(item, dict):
                    hit = _normalize_hit(item)
                    if hit:
                        hits.append(hit)
        policy = payload.get("policy")
        if isinstance(policy, dict):
            hit = _normalize_hit(
                {
                    "document_id": policy.get("document_id"),
                    "filename": policy.get("filename"),
                    "file_path": policy.get("file_path"),
                    "page_or_section": policy.get("policy_version"),
                    "passage": f"Applicable policy ({policy.get('category', 'policy')})",
                    "relevance_score": None,
                }
            )
            if hit:
                hits.append(hit)
        clauses = payload.get("clauses")
        if isinstance(clauses, list):
            for item in clauses:
                if isinstance(item, dict):
                    hit = _normalize_hit(item)
                    if hit:
                        hits.append(hit)
    return hits


def enrich_tool_events_with_documents(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for event in events:
        tool = event.get("tool") or ""
        preview = event.get("_result_content") or event.get("result_preview")
        hits = parse_document_hits(tool, preview)
        if hits:
            event["document_hits"] = hits
    return events


def aggregate_document_sources(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[int, str]] = set()
    aggregated: list[dict[str, Any]] = []
    for event in events:
        for hit in event.get("document_hits") or []:
            doc_id = int(hit["document_id"])
            passage_key = (hit.get("passage") or "")[:240]
            key = (doc_id, passage_key)
            if key in seen:
                continue
            seen.add(key)
            aggregated.append(hit)
    return aggregated
