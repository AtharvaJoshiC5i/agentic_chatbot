"""Numbered reference links (ChatGPT-style) for structured + document sources."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

_LEGACY_SOURCES = re.compile(r"\n\n\*\*Sources\*\*[\s\S]*$", re.IGNORECASE)

_TABLE_KEY_COLUMNS: dict[str, tuple[str, ...]] = {
    "returns": ("return_id",),
    "orders": ("order_id",),
    "order_items": ("order_item_id",),
    "customers": ("customer_id",),
    "products": ("product_id",),
    "inspections": ("inspection_id",),
    "refunds": ("refund_id",),
    "investigation_cases": ("case_id",),
    "product_units": ("product_unit_id", "serial_number"),
}


def _pick_row_key(table: str, item: dict[str, Any]) -> tuple[str, str] | None:
    record = item.get("record") if isinstance(item.get("record"), dict) else {}
    row = (item.get("rows") or [{}])[0] if item.get("rows") else {}
    source: dict[str, Any] = {**row, **record}
    candidates = list(_TABLE_KEY_COLUMNS.get(table, ()))
    candidates.extend(k for k in source if str(k).endswith("_id") or k == "serial_number")
    for col in candidates:
        val = source.get(col)
        if val is not None and str(val).strip():
            return col, str(val).strip()
    return None


def structured_explorer_path(item: dict[str, Any]) -> str:
    table = str(item.get("table_name") or "")
    params = f"tab=structured&table={quote(table)}"
    key = _pick_row_key(table, item)
    if key:
        col, val = key
        params += f"&col={quote(col)}&val={quote(val)}"
    return f"/workspace/data?{params}"


def document_explorer_path(doc: dict[str, Any]) -> str:
    doc_id = int(doc["document_id"])
    params = f"tab=documents&doc={doc_id}"
    page = doc.get("page")
    if page is not None and int(page) > 0:
        params += f"&page={int(page)}"
    passage = (doc.get("passage") or "").strip()
    if passage:
        params += f"&passage={quote(passage[:400])}"
    return f"/workspace/data?{params}"


def build_citations(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    index = 1
    for item in evidence.get("structured") or []:
        label = str(item.get("title") or item.get("table_name") or "Record")
        citations.append(
            {
                "index": index,
                "kind": "structured",
                "label": label,
                "path": structured_explorer_path(item),
                "table_name": item.get("table_name"),
            }
        )
        index += 1
    for doc in evidence.get("documents") or []:
        filename = str(doc.get("filename") or f"Document {doc.get('document_id')}")
        citations.append(
            {
                "index": index,
                "kind": "document",
                "label": filename,
                "path": document_explorer_path(doc),
                "document_id": doc.get("document_id"),
            }
        )
        index += 1
    return citations


def strip_legacy_sources_block(text: str) -> str:
    return _LEGACY_SOURCES.sub("", text.rstrip()).rstrip()


def append_reference_links(text: str, citations: list[dict[str, Any]]) -> str:
    """Append a numbered reference block with markdown links to the data explorer."""
    body = strip_legacy_sources_block(text)
    if not citations:
        return body
    lines = ["", "---", "", "**References**", ""]
    for cite in citations:
        idx = cite["index"]
        label = cite["label"]
        path = cite["path"]
        lines.append(f"{idx}. [{label}]({path})")
    return body + "\n".join(lines)
