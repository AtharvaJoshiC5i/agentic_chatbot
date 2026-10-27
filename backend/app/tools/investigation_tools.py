"""LangGraph tool wrapping the deterministic investigation engine."""

from langchain_core.tools import tool

from app.agents.context import get_agent_db
from app.agents.investigation_documents import gather_investigation_document_sources
from app.investigation.investigation import (
    _load_facts,
    investigation_workflow_context,
    run_investigation,
)
from app.tools.compact import compact_json


@tool
def run_return_investigation(return_id: str) -> str:
    """Run the deterministic investigation checks and policy outcome for a return.

    Response includes a workflow block (active_cases, warehouse_queue_stage) — use it for case status.
    Warehouse managers should prefer get_warehouse_handoff_status for handoff work."""
    session = get_agent_db()
    facts = _load_facts(session, return_id)
    report = run_investigation(session, return_id)
    if report is None:
        return compact_json({"error": "return_not_found", "return_id": return_id})
    policy = report.f3_policy.to_dict() if report.f3_policy else {}
    payload: dict = {
        "return_id": report.return_id,
        "scenario_slug": report.scenario_slug,
        "f2_signal": report.f2_signal,
        "f4_outcome": report.f4_outcome,
        "f3_policy": {
            "product_category": policy.get("product_category"),
            "return_window_days": policy.get("return_window_days"),
            "days_after_delivery": policy.get("days_after_delivery"),
            "within_return_window": policy.get("within_return_window"),
            "within_warranty_period": policy.get("within_warranty_period"),
        },
        "recommended_actions": (report.recommended_actions or [])[:6],
    }
    if facts is not None:
        wf = investigation_workflow_context(session, facts)
        payload["workflow"] = {
            "warehouse_queue_stage": wf.get("warehouse_queue_stage"),
            "analyst_case_open": wf.get("analyst_case_open"),
            "active_cases": wf.get("active_cases"),
            "next_owner": wf.get("next_owner"),
        }
    sources = gather_investigation_document_sources(session, return_id)
    payload["document_source_count"] = len(sources)
    return compact_json(payload)
