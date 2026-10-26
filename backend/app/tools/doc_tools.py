"""LangGraph document retrieval tools (Chroma RAG)."""

from langchain_core.tools import tool

from app.agents.context import get_agent_db
from app.agents.limits import MAX_DOC_SEARCH_RESULTS
from app.models.enums import DocumentAccessLevel, UserRole
from app.rag.search import get_applicable_policy, search_documents
from app.tools.compact import compact_json
from app.agents.context import get_agent_user


def _filter_by_role(results: list) -> list:
    user = get_agent_user()
    if user.role in {UserRole.RETURNS_SUPERVISOR, UserRole.ADMINISTRATOR}:
        return results
    allowed = {DocumentAccessLevel.STANDARD.value, DocumentAccessLevel.RESTRICTED.value}
    return [r for r in results if getattr(r, "access_level", DocumentAccessLevel.STANDARD.value) in allowed]


@tool
def search_return_policy(query: str, category: str | None = None) -> str:
    """Semantic search over return policy documents. Optional category: electronics, fashion, home_appliances, accessories."""
    document_type = "return_policy"
    results = _filter_by_role(search_documents(query, document_type=document_type, limit=MAX_DOC_SEARCH_RESULTS))
    if category:
        cat = category.lower()
        results = [r for r in results if cat.replace("_", "") in r.file_path.lower().replace("_", "")]
    return compact_json([r.source_reference() for r in results])


@tool
def search_inspection_reports(query: str, return_id: str | None = None) -> str:
    """Search warehouse inspection report documents."""
    results = _filter_by_role(
        search_documents(
            query,
            return_id=return_id,
            document_type="inspection_report",
            limit=MAX_DOC_SEARCH_RESULTS,
        )
    )
    return compact_json([r.source_reference() for r in results])


@tool
def search_customer_complaints(query: str, return_id: str | None = None) -> str:
    """Search customer complaint documents."""
    results = _filter_by_role(
        search_documents(
            query,
            return_id=return_id,
            document_type="customer_complaint",
            limit=MAX_DOC_SEARCH_RESULTS,
        )
    )
    return compact_json([r.source_reference() for r in results])


@tool
def search_warranty_documents(query: str, product_id: str | None = None) -> str:
    """Search warranty documents, optionally filtered by product_id metadata."""
    results = search_documents(
        query,
        product_id=product_id,
        document_type="warranty",
        limit=MAX_DOC_SEARCH_RESULTS,
    )
    return compact_json([r.source_reference() for r in results])


@tool
def search_supplier_reports(query: str, product_id: str | None = None) -> str:
    """Search supplier defect reports."""
    results = search_documents(
        query,
        product_id=product_id,
        document_type="supplier_defect_report",
        limit=MAX_DOC_SEARCH_RESULTS,
    )
    return compact_json([r.source_reference() for r in results])


@tool
def resolve_applicable_policy(category: str, relevant_date_iso: str, return_reason: str | None = None) -> str:
    """Select applicable return policy version and retrieve supporting clauses (deterministic metadata + RAG)."""
    from datetime import datetime, timezone

    session = get_agent_db()
    relevant_date = datetime.fromisoformat(relevant_date_iso.replace("Z", "+00:00"))
    if relevant_date.tzinfo is None:
        relevant_date = relevant_date.replace(tzinfo=timezone.utc)
    result = get_applicable_policy(
        session, category, relevant_date, return_reason=return_reason, limit=MAX_DOC_SEARCH_RESULTS
    )
    return compact_json(result)


@tool
def search_support_communications(query: str, return_id: str | None = None) -> str:
    """Search customer-support email communications."""
    results = _filter_by_role(
        search_documents(
            query,
            return_id=return_id,
            document_type="support_communication",
            limit=MAX_DOC_SEARCH_RESULTS,
        )
    )
    return compact_json([r.source_reference() for r in results])


@tool
def search_refurbishment_guidelines(query: str, product_id: str | None = None) -> str:
    """Search refurbishment / resale quality guidelines."""
    results = _filter_by_role(
        search_documents(
            query,
            product_id=product_id,
            document_type="refurbishment_guideline",
            limit=MAX_DOC_SEARCH_RESULTS,
        )
    )
    return compact_json([r.source_reference() for r in results])


DOCUMENT_TOOLS = [
    search_return_policy,
    search_inspection_reports,
    search_customer_complaints,
    search_warranty_documents,
    search_supplier_reports,
    search_support_communications,
    search_refurbishment_guidelines,
    resolve_applicable_policy,
]
