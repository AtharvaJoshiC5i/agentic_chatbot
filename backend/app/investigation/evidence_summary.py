"""Structured evidence summary for contradiction detection."""

from typing import Any

from sqlalchemy.orm import Session

from app.investigation.investigation import run_investigation


def detect_return_inconsistencies(session: Session, return_id: str) -> dict[str, Any]:
    report = run_investigation(session, return_id)
    if report is None:
        return {"return_id": return_id, "error": "not_found"}

    confirmed: list[dict[str, Any]] = []
    disputed: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    for check in report.checks:
        entry = {
            "check_id": check.check_id,
            "title": check.title,
            "summary": check.summary,
            "status": check.status,
        }
        if check.status == "fail":
            disputed.append(entry)
        elif check.status == "warn":
            gaps.append(entry)
        elif check.status == "pass":
            confirmed.append(entry)

    return {
        "return_id": return_id,
        "primary_signal": report.f2_signal,
        "investigation_outcome": report.f4_outcome,
        "confirmed": confirmed,
        "disputed": disputed,
        "gaps": gaps,
        "recommended_actions": report.recommended_actions,
    }
