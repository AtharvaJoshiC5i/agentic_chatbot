"""Chat visuals are built from the database for the tools that ran (no LLM)."""

from app.agents.context import clear_agent_context, set_agent_context
from app.agents.visuals import build_visuals
from app.models.enums import UserRole
from app.security.deps import CurrentUser
from app.synthetic.generator import generate_synthetic_data
from app.synthetic.loader import load_bundle


def test_visuals_for_key_scenarios(db_session) -> None:
    load_bundle(db_session, generate_synthetic_data())
    set_agent_context(db_session, CurrentUser(user_id=1, username="t", role=UserRole.RETURNS_SUPERVISOR))
    try:
        by_type = lambda events, focus=None: {v["type"]: v for v in build_visuals(events, focus)}  # noqa: E731

        v = by_type([{"tool": "run_return_investigation", "args": {"return_id": "R103"}}])
        assert v["return_window"]["days_after_delivery"] == 55 and v["return_window"]["within_window"] is False
        assert v["investigation"]["checks"]

        ev = by_type([{"tool": "get_inspection_results", "args": {"return_id": "R102"}}])["evidence"]
        assert ev["purchased_serial"] == "HP9081" and ev["inspections"][0]["serial_match"] is False

        rec = by_type([{"tool": "get_recovery_recommendation", "args": {"return_id": "R115"}}])["recovery"]
        assert rec["unsafe"] and rec["recommended_method"] in ("recycle", "dispose")

        led = by_type([{"tool": "get_refund_status", "args": {}}], "R106")["refund_ledger"]
        assert led["has_completed"] and led["refunds"][0]["amount_inr"] == 2499.0

        q = by_type([{"tool": "list_refunds_awaiting_approval", "args": {}}])["refund_queue"]
        assert q["count"] > 0 and q["total_inr"] > 0

        assert build_visuals([{"tool": "search_return_policy", "args": {}}], None) == []
    finally:
        clear_agent_context()
