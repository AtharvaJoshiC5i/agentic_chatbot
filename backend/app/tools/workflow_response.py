"""Compact post-action state for the agent's observe → act → verify loop."""

from sqlalchemy.orm import Session

from app.services.return_workflow import build_return_workflow_snapshot


def current_workflow_handoff(session: Session, return_id: str) -> dict:
    snapshot = build_return_workflow_snapshot(session, return_id)
    if snapshot.get("error"):
        return {"return_id": return_id, "error": snapshot["error"]}
    return {
        "return_id": snapshot["return_id"],
        "return_status": snapshot["return_status"],
        "stage": snapshot["analyst_workflow_stage"],
        "next_owner": snapshot["next_owner"],
        "next_step": snapshot["status_summary"],
        "payment_note": "Demo ledger state only; no payment provider is connected."
        if snapshot.get("refund")
        else None,
        "notification_note": "Message confirmation is recorded locally; no email is delivered."
        if snapshot.get("notification")
        else None,
    }
