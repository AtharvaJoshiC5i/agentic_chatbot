"""Persisted Decision Passport reports."""

import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.investigation.investigation import run_investigation
from app.models.tables import ActionRequest, AuditLog, DecisionPassport, Return
from app.services.timeline import build_return_timeline


def _format_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Decision Passport — {payload.get('return_id', 'unknown')}",
        "",
        f"**Outcome:** {payload.get('investigation_outcome', 'n/a')}",
        f"**Signal:** {payload.get('primary_signal', 'n/a')}",
        "",
        "## Confirmed findings",
    ]
    for item in payload.get("confirmed_findings", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Contradictions / gaps"])
    for item in payload.get("gaps_and_contradictions", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Recommended actions"])
    for item in payload.get("recommended_actions", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Executed actions"])
    for item in payload.get("executed_actions", []):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def build_passport_payload(session: Session, return_id: str) -> dict[str, Any]:
    if session.get(Return, return_id) is None:
        raise ValueError("Return not found")

    investigation = run_investigation(session, return_id)
    timeline = build_return_timeline(session, return_id, sync=True)

    gaps: list[str] = []
    confirmed: list[str] = []
    if investigation:
        for check in investigation.checks:
            if check.status == "fail":
                gaps.append(f"{check.title}: {check.summary}")
            elif check.status in ("pass", "warn"):
                confirmed.append(f"{check.title}: {check.summary}")

    actions = session.execute(
        select(ActionRequest)
        .where(ActionRequest.return_id == return_id)
        .order_by(ActionRequest.created_at.desc())
        .limit(20)
    ).scalars().all()
    executed = [
        f"{a.action_type} #{a.action_id} — {a.execution_status}"
        for a in actions
        if a.execution_status == "succeeded"
    ]
    pending = [
        f"{a.action_type} #{a.action_id} — awaiting {a.approval_status}"
        for a in actions
        if a.execution_status in ("awaiting_approval", "approved", "pending")
    ]

    audits = session.execute(
        select(AuditLog)
        .where(AuditLog.target_id == return_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(10)
    ).scalars().all()

    return {
        "return_id": return_id,
        "generated_at": utc_now().isoformat(),
        "investigation_outcome": investigation.f4_outcome if investigation else None,
        "primary_signal": investigation.f2_signal if investigation else None,
        "policy": investigation.f3_policy.to_dict() if investigation else None,
        "confirmed_findings": confirmed,
        "gaps_and_contradictions": gaps,
        "recommended_actions": investigation.recommended_actions if investigation else [],
        "timeline_event_count": len(timeline),
        "executed_actions": executed,
        "pending_actions": pending,
        "recent_audit_count": len(audits),
    }


def save_decision_passport(session: Session, return_id: str) -> DecisionPassport:
    payload = build_passport_payload(session, return_id)
    current_version = session.execute(
        select(func.max(DecisionPassport.version)).where(DecisionPassport.return_id == return_id)
    ).scalar_one()
    version = int(current_version or 0) + 1
    markdown = _format_markdown(payload)
    row = DecisionPassport(
        return_id=return_id,
        version=version,
        payload_json=json.dumps(payload, default=str),
        markdown_report=markdown,
        created_at=utc_now(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_latest_passport(session: Session, return_id: str) -> DecisionPassport | None:
    return session.execute(
        select(DecisionPassport)
        .where(DecisionPassport.return_id == return_id)
        .order_by(DecisionPassport.version.desc())
    ).scalars().first()
