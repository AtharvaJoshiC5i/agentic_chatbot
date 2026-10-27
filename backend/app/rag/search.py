"""Semantic search and policy retrieval over ChromaDB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import DocumentType
from app.models.tables import DocumentMetadata
from app.rag.embeddings import get_embedder
from app.rag.store import get_document_collection

CATEGORY_POLICY_FILES: dict[str, str] = {
    "electronics": "electronics",
    "fashion": "fashion",
    "home_appliances": "home_appliances",
    "accessories": "accessories",
}


@dataclass(frozen=True)
class DocumentSearchResult:
    document_id: int
    filename: str
    document_type: str
    file_path: str
    return_id: str | None
    product_id: str | None
    policy_version: str | None
    page: int | None
    section: str | None
    passage: str
    relevance_score: float

    def source_reference(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "file_path": self.file_path,
            "page_or_section": self.section or (f"Page {self.page}" if self.page else None),
            "page": self.page,
            "passage": self.passage,
            "relevance_score": self.relevance_score,
        }


def _build_where_filter(
    *,
    return_id: str | None,
    product_id: str | None,
    document_type: str | None,
) -> dict[str, Any] | None:
    clauses: list[dict[str, Any]] = []
    if return_id:
        clauses.append({"return_id": return_id})
    if product_id:
        clauses.append({"product_id": product_id})
    if document_type:
        clauses.append({"document_type": document_type})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def search_documents(
    query: str,
    *,
    return_id: str | None = None,
    product_id: str | None = None,
    document_type: str | None = None,
    limit: int = 5,
) -> list[DocumentSearchResult]:
    collection = get_document_collection()
    if collection.count() == 0:
        return []

    embedder = get_embedder()
    where = _build_where_filter(
        return_id=return_id,
        product_id=product_id,
        document_type=document_type,
    )

    results = collection.query(
        query_embeddings=[embedder.embed_query(query)],
        n_results=min(limit, max(collection.count(), 1)),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    return _parse_chroma_results(results)


def get_applicable_policy(
    session: Session,
    category: str,
    relevant_date: datetime,
    return_reason: str | None = None,
    *,
    limit: int = 5,
) -> dict[str, Any]:
    """
    Select the applicable return policy version from metadata, then retrieve clauses from Chroma.
    """
    policies = session.execute(
        select(DocumentMetadata).where(
            DocumentMetadata.document_type == DocumentType.RETURN_POLICY.value
        )
    ).scalars().all()

    comparison_date = _as_utc(relevant_date)
    candidates = [
        policy
        for policy in policies
        if _policy_matches_category(policy.file_path, category)
        and (
            policy.effective_date is None
            or _as_utc(policy.effective_date) <= comparison_date
        )
    ]

    if not candidates:
        return {
            "policy": None,
            "clauses": [],
            "message": f"No policy document found for category={category}",
        }

    def sort_key(doc: DocumentMetadata) -> tuple:
        effective = (
            _as_utc(doc.effective_date)
            if doc.effective_date
            else datetime.fromtimestamp(0, tz=timezone.utc)
        )
        version = doc.policy_version or ""
        return (effective, version)

    selected = max(candidates, key=sort_key)
    query_parts = [f"{category} return policy", "return window", "eligibility"]
    if return_reason:
        query_parts.append(return_reason.replace("_", " "))
    query = " ".join(query_parts)

    clauses = search_documents(
        query,
        document_type=DocumentType.RETURN_POLICY.value,
        limit=limit,
    )
    clauses = [c for c in clauses if c.document_id == selected.document_id] or clauses

    return {
        "policy": {
            "document_id": selected.document_id,
            "filename": selected.filename,
            "policy_version": selected.policy_version,
            "effective_date": selected.effective_date.isoformat() if selected.effective_date else None,
            "file_path": selected.file_path,
            "category": category,
        },
        "clauses": [clause.source_reference() for clause in clauses],
    }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _policy_matches_category(file_path: str, category: str) -> bool:
    path = file_path.lower()
    if category == "damaged_products":
        return "damaged" in path
    token = CATEGORY_POLICY_FILES.get(category, category).lower()
    normalized_path = path.replace("_", "")
    return token.replace("_", "") in normalized_path


def _parse_chroma_results(results: dict) -> list[DocumentSearchResult]:
    parsed: list[DocumentSearchResult] = []
    if not results.get("ids") or not results["ids"][0]:
        return parsed

    for index, chunk_id in enumerate(results["ids"][0]):
        metadata = results["metadatas"][0][index]
        document = results["documents"][0][index]
        distance = results["distances"][0][index] if results.get("distances") else 0.0
        page_raw = metadata.get("page", -1)
        page = int(page_raw) if int(page_raw) >= 0 else None
        parsed.append(
            DocumentSearchResult(
                document_id=int(metadata["document_id"]),
                filename=metadata.get("filename", ""),
                document_type=metadata.get("document_type", ""),
                file_path=metadata.get("file_path", ""),
                return_id=metadata.get("return_id") or None,
                product_id=metadata.get("product_id") or None,
                policy_version=metadata.get("policy_version") or None,
                page=page,
                section=metadata.get("section") or None,
                passage=document,
                relevance_score=1.0 - float(distance),
            )
        )
    return parsed
