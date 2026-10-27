"""Attach unstructured document citations to deterministic investigation (all personas)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agents.document_citations import _normalize_hit
from app.investigation.investigation import _load_facts
from app.models.enums import DocumentType
from app.rag.search import get_applicable_policy, search_documents


def gather_investigation_document_sources(session: Session, return_id: str) -> list[dict[str, Any]]:
    """Policy + return-scoped documents every investigation should surface as sources."""
    facts = _load_facts(session, return_id.strip().upper())
    if facts is None:
        return []

    category = facts.product.category or "accessories"
    return_reason = facts.return_row.return_reason
    request_date = facts.return_row.request_date
    product_id = facts.product.product_id

    seen: set[tuple[int, str]] = set()
    hits: list[dict[str, Any]] = []

    def add_from_refs(refs: list[dict[str, Any]]) -> None:
        for raw in refs:
            hit = _normalize_hit(raw)
            if not hit:
                continue
            key = (hit["document_id"], (hit.get("passage") or "")[:200])
            if key in seen:
                continue
            seen.add(key)
            hits.append(hit)

    policy_payload = get_applicable_policy(
        session,
        category,
        request_date,
        return_reason,
        limit=4,
    )
    policy = policy_payload.get("policy")
    if isinstance(policy, dict) and policy.get("document_id"):
        add_from_refs(
            [
                {
                    "document_id": policy["document_id"],
                    "filename": policy.get("filename"),
                    "file_path": policy.get("file_path"),
                    "page_or_section": policy.get("policy_version"),
                    "passage": f"Applicable {category} return policy ({policy.get('policy_version') or 'policy'}).",
                    "page": None,
                }
            ]
        )
    clauses = policy_payload.get("clauses")
    if isinstance(clauses, list):
        add_from_refs(clauses)

    for document_type, query in (
        (DocumentType.CUSTOMER_COMPLAINT.value, f"customer complaint return {return_id}"),
        (DocumentType.INSPECTION_REPORT.value, f"warehouse inspection {return_id}"),
        (DocumentType.WARRANTY.value, f"warranty coverage {product_id}"),
        (DocumentType.SUPPORT_COMMUNICATION.value, f"support email return {return_id}"),
    ):
        results = search_documents(
            query,
            return_id=return_id,
            product_id=product_id if document_type == DocumentType.WARRANTY.value else None,
            document_type=document_type,
            limit=2,
        )
        add_from_refs([r.source_reference() for r in results])

    return hits[:12]
