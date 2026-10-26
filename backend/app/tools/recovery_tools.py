"""LangGraph tools for recovery optimization (F6)."""

from langchain_core.tools import tool

from app.agents.context import get_agent_db
from app.services.recovery_optimizer import RecoveryOptimizerError, list_recovery_options, optimize_recovery
from app.tools.compact import compact_json


@tool
def get_recovery_options(return_id: str) -> str:
    """List modeled recovery options and net recovery values for a return."""
    session = get_agent_db()
    rows = list_recovery_options(session, return_id)
    if not rows:
        return compact_json({"return_id": return_id, "options": []})
    return compact_json(
        [
            {
                "option_id": row.option_id,
                "recovery_method": row.recovery_method,
                "expected_net_recovery_paise": row.expected_net_recovery,
                "feasibility_status": row.feasibility_status,
            }
            for row in rows
        ]
    )


@tool
def get_recovery_recommendation(return_id: str) -> str:
    """Run the deterministic recovery optimizer (max net recovery, safety filters)."""
    session = get_agent_db()
    try:
        recommendation = optimize_recovery(session, return_id)
    except RecoveryOptimizerError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json(recommendation.to_dict())
