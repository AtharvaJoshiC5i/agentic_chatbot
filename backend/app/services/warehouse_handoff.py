"""Warehouse handoff context (aligned with inspection queue)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import ReturnStatus
from app.models.tables import Inspection, Return
from app.services.cases import get_active_case
from app.services.handoff import get_latest_verdict
from app.services.warehouse_queue import _is_received


def get_warehouse_handoff_status(session: Session, return_id: str) -> dict[str, Any]:
    session.expire_all()
    row = session.get(Return, return_id)
    if row is None:
        return {"error": "not_found", "message": "Return not found", "return_id": return_id}

    active = get_active_case(session, return_id)
    insp_count = int(
        session.execute(
            select(func.count()).select_from(Inspection).where(Inspection.return_id == return_id)
        ).scalar_one()
    )
    received = _is_received(row)

    if active is None:
        queue_stage = "no_handoff"
        next_step = "No analyst investigation case — warehouse handoff not required."
    elif insp_count > 0 and get_latest_verdict(session, return_id) is None:
        queue_stage = "verdict"
        next_step = "Inspection recorded. Give your verdict: can the refund or replacement be performed?"
    elif insp_count > 0:
        queue_stage = "verdict_given"
        next_step = "Verdict recorded. The returns analyst decides whether to submit it to the supervisor."
    elif received:
        queue_stage = "inspect"
        next_step = "Record warehouse inspection (condition, defect verified, result, notes)."
    else:
        queue_stage = "receive"
        next_step = "Record warehouse receipt when the unit arrives, then record inspection."

    active_case = None
    if active is not None:
        active_case = {
            "case_id": active.case_id,
            "case_status": active.case_status,
            "issue_type": active.issue_type,
            "priority": active.priority,
        }

    inspections = list(
        session.execute(
            select(Inspection).where(Inspection.return_id == return_id).order_by(Inspection.inspection_id)
        ).scalars().all()
    )
    latest_insp = None
    if inspections:
        last = inspections[-1]
        latest_insp = {
            "inspection_id": last.inspection_id,
            "inspection_result": last.inspection_result,
            "defect_verified": last.defect_verified,
            "product_condition": last.product_condition,
        }

    return {
        "return_id": return_id,
        "return_status": row.return_status,
        "requested_resolution": row.requested_resolution,
        "return_reason": row.return_reason,
        "received_at_warehouse": received,
        "received_date": row.received_date.isoformat() if row.received_date else None,
        "inspection_count": insp_count,
        "latest_inspection": latest_insp,
        "active_case": active_case,
        "warehouse_queue_stage": queue_stage,
        "next_warehouse_step": next_step,
        "analyst_case_open": active is not None,
    }
