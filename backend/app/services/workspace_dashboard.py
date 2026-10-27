"""Role-scoped workspace dashboard payloads."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import ApprovalStatus, UserRole
from app.models.tables import ActionRequest
from app.security.deps import CurrentUser
from app.services.analyst_queue import analyst_queue_kpis, build_analyst_work_queue
from app.services.queue_activity import (
    PERSONA_ANALYST,
    PERSONA_SUPERVISOR,
    PERSONA_WAREHOUSE,
    apply_persona_queue_order,
    build_recent_updates,
    enrich_queue_items,
)
from app.services.supervisor_queue import build_supervisor_approval_queue, supervisor_queue_kpis
from app.services.timeline import build_return_timeline
from app.services.warehouse_queue import build_warehouse_work_queue, warehouse_queue_kpis

SUPERVISOR_APPROVALS_DISPLAY_LIMIT = 50


def _workspace_persona(user: CurrentUser) -> str:
    if user.role in {UserRole.RETURNS_SUPERVISOR, UserRole.ADMINISTRATOR}:
        return PERSONA_SUPERVISOR
    if user.role == UserRole.WAREHOUSE_MANAGER:
        return PERSONA_WAREHOUSE
    return PERSONA_ANALYST


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


def _finalize_queue_section(
    session: Session,
    persona: str,
    section_key: str,
    section_title: str,
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    enrich_queue_items(session, items, persona, sync_timeline=False)
    apply_persona_queue_order(items, persona)
    recent = build_recent_updates(items)
    sections: list[dict[str, Any]] = []
    if recent:
        sections.append(_section("recent_updates", "Latest updates", recent))
    sections.append(_section(section_key, section_title, items))
    return sections


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

    sections = _finalize_queue_section(
        session, PERSONA_ANALYST, "work_queue", "Return requests", work_queue
    )
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
    sections = _finalize_queue_section(
        session, PERSONA_WAREHOUSE, "warehouse_handoffs", "Inspection queue", handoffs
    )
    return {"kpis": kpis, "sections": sections}


def _build_supervisor(session: Session, _user: CurrentUser) -> dict[str, Any]:
    queue = build_supervisor_approval_queue(session)
    enrich_queue_items(session, queue, PERSONA_SUPERVISOR, sync_timeline=False)
    apply_persona_queue_order(queue, PERSONA_SUPERVISOR)
    recent = build_recent_updates(queue)

    displayed = queue[:SUPERVISOR_APPROVALS_DISPLAY_LIMIT]
    for item in displayed:
        rid = item.get("return_id")
        if rid:
            item["workflow_timeline"] = build_return_timeline(session, rid, sync=False)

    sections: list[dict[str, Any]] = []
    if recent:
        sections.append(_section("recent_updates", "Latest updates", recent))
    sections.append(_section("approval_queue", "Pending approvals", displayed))

    kpis = supervisor_queue_kpis(queue, shown=len(displayed))
    return {"kpis": kpis, "sections": sections}


def get_workspace_dashboard(session: Session, user: CurrentUser) -> dict[str, Any]:
    persona = _workspace_persona(user)
    if persona == PERSONA_SUPERVISOR:
        body = _build_supervisor(session, user)
    elif persona == PERSONA_WAREHOUSE:
        body = _build_warehouse(session, user)
    else:
        body = _build_analyst(session, user)

    return {
        "persona": persona,
        "generated_at": utc_now(),
        "kpis": body["kpis"],
        "sections": body["sections"],
    }
