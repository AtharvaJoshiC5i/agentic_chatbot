"""LangGraph tool wrapping the deterministic investigation engine."""

from langchain_core.tools import tool

from app.agents.context import get_agent_db
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
    payload = report.to_dict()
    payload.pop("checks", None)
    if facts is not None:
        payload["workflow"] = investigation_workflow_context(session, facts)
    return compact_json(payload)
