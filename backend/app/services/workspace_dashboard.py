"""Role-scoped workspace dashboard payloads."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import ApprovalStatus, UserRole
from app.models.tables import ActionRequest
from app.security.deps import CurrentUser
from app.services.analyst_queue import analyst_queue_kpis, build_analyst_work_queue
from app.services.supervisor_queue import build_supervisor_approval_queue, supervisor_queue_kpis
from app.services.warehouse_queue import build_warehouse_work_queue, warehouse_queue_kpis


def _workspace_persona(user: CurrentUser) -> str:
    if user.role in {UserRole.RETURNS_SUPERVISOR, UserRole.ADMINISTRATOR}:
        return "returns_supervisor"
    if user.role == UserRole.WAREHOUSE_MANAGER:
        return "warehouse_manager"
    return "returns_analyst"


def _section(key: str, title: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {"key": key, "title": title, "items": items}


def _action_item(row: ActionRequest) -> dict[str, Any]:
    return {
        "kind": "pending_action",
        "action_id": row.action_id,
        "return_id": row.return_id,
        "title": row.action_type.replace("_", " ").title(),
        "subtitle": f"Approval {row.approval_status}",
        "status": row.approval_status,
    }


def _build_analyst(session: Session, user: CurrentUser) -> dict[str, Any]:
    work_queue = build_analyst_work_queue(session)
    kpis = analyst_queue_kpis(work_queue)

    pending_actions = list(
        session.execute(
            select(ActionRequest)
            .where(
                ActionRequest.requested_by == user.username,
                ActionRequest.approval_status == ApprovalStatus.PENDING.value,
            )
            .order_by(ActionRequest.action_id.desc())
            .limit(10)
        ).scalars().all()
    )

    sections = [
        # One list, ordered so "your move" items come first; each item carries `your_move`.
        _section("work_queue", "Return requests", work_queue),
    ]
    if pending_actions:
        sections.append(
            _section(
                "my_pending_requests",
                "Your pending submissions",
                [_action_item(a) for a in pending_actions],
            )
        )
    return {"kpis": kpis, "sections": sections}


def _build_warehouse(session: Session, _user: CurrentUser) -> dict[str, Any]:
    handoffs = build_warehouse_work_queue(session)
    kpis = warehouse_queue_kpis(handoffs)
    sections = [
        _section("warehouse_handoffs", "Inspection queue", handoffs),
    ]
    return {"kpis": kpis, "sections": sections}


def _build_supervisor(session: Session, _user: CurrentUser) -> dict[str, Any]:
    queue = build_supervisor_approval_queue(session, limit=200)
    kpis = supervisor_queue_kpis(queue)
    sections = [
        _section("approval_queue", "Pending approvals", queue),
    ]
    return {"kpis": kpis, "sections": sections}


def get_workspace_dashboard(session: Session, user: CurrentUser) -> dict[str, Any]:
    persona = _workspace_persona(user)
    if persona == "returns_supervisor":
        body = _build_supervisor(session, user)
    elif persona == "warehouse_manager":
        body = _build_warehouse(session, user)
    else:
        body = _build_analyst(session, user)

    return {
        "persona": persona,
        "generated_at": utc_now(),
        "kpis": body["kpis"],
        "sections": body["sections"],
    }
