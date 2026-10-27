"""Cross-persona queue activity: latest timeline event per return, sort, and highlight handoffs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.tables import ReturnEvent
from app.services.return_events import sync_return_timeline

RECENT_UPDATES_LIMIT = 8

PERSONA_ANALYST = "returns_analyst"
PERSONA_WAREHOUSE = "warehouse_manager"
PERSONA_SUPERVISOR = "returns_supervisor"


def _ts_key(value: datetime | str | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, datetime):
        return value.timestamp()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def event_actor_persona(event: ReturnEvent) -> str:
    """Map a timeline row to the persona who caused it (best effort from type + description)."""
    d = event.description.lower()
    sid = (event.source_id or "").lower()
    et = event.event_type

    if et in ("inspection_completed", "warehouse_received"):
        return PERSONA_WAREHOUSE
    if "warehouse verdict" in d or sid.startswith("verdict:"):
        return PERSONA_WAREHOUSE
    if "picked up by warehouse" in d or "warehouse_claimed" in sid:
        return PERSONA_WAREHOUSE

    if et == "investigation_opened":
        return PERSONA_ANALYST
    if "handed to warehouse" in d or "warehouse_handoff" in sid:
        return PERSONA_ANALYST
    if "moved to investigating" in d or sid.endswith(":investigating"):
        return PERSONA_ANALYST
    if et == "refund_requested":
        return PERSONA_ANALYST
    if "replacement request" in d or ("replacement" in d and "awaiting supervisor" in d):
        return PERSONA_ANALYST
    if sid.startswith("replacement:") and ":requested" in sid:
        return PERSONA_ANALYST
    if "submitted" in d and "supervisor" in d:
        return PERSONA_ANALYST
    if "declined" in d and "return" in d:
        return PERSONA_ANALYST
    if "policy" in d:
        return PERSONA_ANALYST
    if et == "case_updated" and ("assigned to" in d or "automatically assigned" in d):
        return PERSONA_ANALYST

    if et == "refund_processed":
        return PERSONA_SUPERVISOR
    if "supervisor" in d:
        return PERSONA_SUPERVISOR
    if ("approved" in d or "rejected" in d) and ("refund" in d or "replacement" in d):
        return PERSONA_SUPERVISOR

    return "system"


def _actor_label(persona: str) -> str:
    return {
        PERSONA_ANALYST: "Returns analyst",
        PERSONA_WAREHOUSE: "Warehouse",
        PERSONA_SUPERVISOR: "Supervisor",
        "system": "System",
    }.get(persona, persona.replace("_", " ").title())


def fetch_latest_events(session: Session, return_ids: list[str]) -> dict[str, ReturnEvent]:
    """Latest event per return by timestamp (sync backfill must not beat real handoffs on event_id)."""
    if not return_ids:
        return {}
    ts_subq = (
        select(
            ReturnEvent.return_id,
            func.max(ReturnEvent.event_timestamp).label("max_ts"),
        )
        .where(ReturnEvent.return_id.in_(return_ids))
        .group_by(ReturnEvent.return_id)
        .subquery()
    )
    rows = session.execute(
        select(ReturnEvent)
        .join(
            ts_subq,
            (ReturnEvent.return_id == ts_subq.c.return_id)
            & (ReturnEvent.event_timestamp == ts_subq.c.max_ts),
        )
        .order_by(ReturnEvent.return_id, ReturnEvent.event_id.desc())
    ).scalars().all()
    latest: dict[str, ReturnEvent] = {}
    for row in rows:
        if row.return_id not in latest:
            latest[row.return_id] = row
    return latest


def enrich_queue_items(
    session: Session,
    items: list[dict[str, Any]],
    viewer_persona: str,
    *,
    sync_timeline: bool = True,
) -> list[dict[str, Any]]:
    """Attach last_activity_* fields and handoff flags; optionally sync events from structured data."""
    return_ids = list({i["return_id"] for i in items if i.get("return_id")})
    if not return_ids:
        return items

    if sync_timeline:
        for rid in return_ids[:120]:
            sync_return_timeline(session, rid, commit=False)
        session.flush()

    latest = fetch_latest_events(session, return_ids)
    for item in items:
        rid = item.get("return_id")
        if not rid:
            continue
        ev = latest.get(rid)
        if ev is None:
            item.setdefault("handoff_from_other", False)
            item.setdefault("is_highlighted", False)
            continue
        actor = event_actor_persona(ev)
        item["last_activity_at"] = ev.event_timestamp
        item["last_update_summary"] = ev.description
        item["last_update_actor"] = actor
        item["last_update_actor_label"] = _actor_label(actor)
        item["handoff_from_other"] = actor not in (viewer_persona, "system")
        item["is_highlighted"] = bool(item["handoff_from_other"])
    return items


def build_recent_updates(items: list[dict[str, Any]], *, limit: int = RECENT_UPDATES_LIMIT) -> list[dict[str, Any]]:
    highlighted = [i for i in items if i.get("is_highlighted") and i.get("return_id")]
    highlighted.sort(key=lambda x: _ts_key(x.get("last_activity_at")), reverse=True)
    return highlighted[:limit]


def sort_analyst_queue(items: list[dict[str, Any]]) -> None:
    from app.services.analyst_queue import _stage_rank

    items.sort(
        key=lambda x: (
            0 if x.get("handoff_from_other") else 1,
            0 if x.get("your_move") else 1,
            _stage_rank(x.get("workflow_stage") or ""),
            -_ts_key(x.get("last_activity_at")),
            x.get("return_id") or "",
        )
    )


def sort_warehouse_queue(items: list[dict[str, Any]]) -> None:
    rank = {"receive": 0, "inspect": 1, "verdict": 2}
    items.sort(
        key=lambda x: (
            0 if x.get("handoff_from_other") else 1,
            -_ts_key(x.get("last_activity_at")),
            rank.get(x.get("workflow_stage"), 9),
            x.get("return_id") or "",
        )
    )


def sort_supervisor_queue(items: list[dict[str, Any]]) -> None:
    items.sort(
        key=lambda x: (
            0 if x.get("handoff_from_other") else 1,
            -_ts_key(x.get("last_activity_at")),
            -(x.get("refund_id") or 0),
            -(x.get("replacement_id") or 0),
            -(x.get("action_id") or 0),
            x.get("return_id") or "",
        )
    )


def apply_persona_queue_order(items: list[dict[str, Any]], persona: str) -> None:
    if persona == PERSONA_WAREHOUSE:
        sort_warehouse_queue(items)
    elif persona == PERSONA_SUPERVISOR:
        sort_supervisor_queue(items)
    else:
        sort_analyst_queue(items)
