"""Read-only portfolio tools: lists and summaries across returns (all roles may read)."""

from datetime import datetime, timezone

from langchain_core.tools import tool
from sqlalchemy import func, select

from app.agents.context import get_agent_db
from app.models.enums import CaseStatus
from app.models.tables import ActionRequest, InvestigationCase, OrderItem, Product, Refund, Return, Supplier
from app.services.monitoring import get_monitoring_summary
from app.tools.compact import compact_json


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@tool
def list_returns(status: str | None = None, limit: int = 15) -> str:
    """List returns, optionally filtered by status (requested, approved, pickup_scheduled, in_transit,
    received, inspecting, investigating, resolved, rejected, closed). Newest requests first."""
    session = get_agent_db()
    query = select(Return).order_by(Return.request_date.desc()).limit(max(1, min(limit, 50)))
    if status:
        query = query.where(Return.return_status == status.strip().lower())
    rows = session.execute(query).scalars().all()
    return compact_json(
        {
            "status_filter": status,
            "count": len(rows),
            "returns": [
                {"return_id": r.return_id, "status": r.return_status, "reason": r.return_reason,
                 "requested": str(r.request_date)[:10]}
                for r in rows
            ],
        }
    )


@tool
def list_refunds_awaiting_approval(limit: int = 15) -> str:
    """List refund requests that are still pending approval (refund_status requested, approval pending)."""
    session = get_agent_db()
    rows = session.execute(
        select(Refund)
        .where(Refund.refund_status == "requested", Refund.approval_status == "pending")
        .order_by(Refund.refund_id)
        .limit(max(1, min(limit, 50)))
    ).scalars().all()
    return compact_json(
        {
            "count_returned": len(rows),
            "refunds": [
                {"refund_id": r.refund_id, "return_id": r.return_id,
                 "amount_inr": round(r.refund_amount / 100, 2), "status": r.refund_status,
                 "approval": r.approval_status}
                for r in rows
            ],
        }
    )


def list_open_investigation_case_rows(
    session,
    *,
    overdue_only: bool = False,
) -> list[dict]:
    """Shared query for the portfolio tool and chat visuals (not JSON-truncated)."""
    rows = session.execute(
        select(InvestigationCase)
        .where(InvestigationCase.case_status.notin_([CaseStatus.RESOLVED.value, CaseStatus.CLOSED.value]))
        .order_by(InvestigationCase.due_date)
    ).scalars().all()
    now = datetime.now(timezone.utc)
    items: list[dict] = []
    for case in rows:
        due = _utc(case.due_date)
        overdue = bool(due and due < now)
        if overdue_only and not overdue:
            continue
        items.append(
            {
                "case_id": case.case_id,
                "return_id": case.return_id,
                "issue_type": case.issue_type,
                "priority": case.priority,
                "status": case.case_status,
                "assigned_to": case.assigned_to,
                "due": str(due)[:10] if due else None,
                "overdue": overdue,
            }
        )
    return items


@tool
def list_open_investigation_cases(overdue_only: bool = False, limit: int = 15) -> str:
    """List investigation cases that are not resolved/closed, with assignee, priority and due date.
    Set overdue_only=true to list only cases past their due date."""
    session = get_agent_db()
    items = list_open_investigation_case_rows(session, overdue_only=overdue_only)
    cap = max(1, min(limit, 50))
    return compact_json({"total_matching": len(items), "cases": items[:cap]})


@tool
def list_actions_for_return(return_id: str) -> str:
    """List action requests (refund requests, case creation, recovery tasks) for a return, with approval/execution status."""
    session = get_agent_db()
    rows = session.execute(
        select(ActionRequest).where(ActionRequest.return_id == return_id.strip().upper()).order_by(ActionRequest.action_id)
    ).scalars().all()
    return compact_json(
        {
            "return_id": return_id.upper(),
            "count": len(rows),
            "actions": [
                {"action_id": a.action_id, "type": a.action_type, "requested_by": a.requested_by,
                 "approval": a.approval_status, "execution": a.execution_status}
                for a in rows
            ],
        }
    )


@tool
def summarize_returns(group_by: str = "reason", status: str | None = None) -> str:
    """Count returns grouped by reason, status, category or supplier (optional status filter).
    Use this to build charts such as 'returns by reason' or 'returns per supplier'."""
    session = get_agent_db()
    key = group_by.strip().lower()
    columns = {
        "reason": Return.return_reason,
        "status": Return.return_status,
        "category": Product.category,
        "supplier": Supplier.supplier_name,
    }
    if key not in columns:
        return compact_json({"error": "invalid_group_by", "allowed": sorted(columns)})
    query = (
        select(columns[key].label("bucket"), func.count(Return.return_id).label("returns"))
        .select_from(Return)
        .join(OrderItem, OrderItem.order_item_id == Return.order_item_id)
        .join(Product, Product.product_id == OrderItem.product_id)
        .join(Supplier, Supplier.supplier_id == Product.supplier_id)
        .group_by(columns[key])
        .order_by(func.count(Return.return_id).desc())
        .limit(10)
    )
    if status:
        query = query.where(Return.return_status == status.strip().lower())
    rows = session.execute(query).all()
    return compact_json({"group_by": key, "status_filter": status, "groups": [{"name": r.bucket, "returns": r.returns} for r in rows]})


@tool
def get_monitoring_overview() -> str:
    """Summarise system health: open monitoring alerts (overdue investigations, pending refund approvals, etc.)."""
    session = get_agent_db()
    summary = get_monitoring_summary(session)
    alerts = summary.get("alerts", [])[:10]
    return compact_json({"open_alerts": summary.get("open_alerts", 0), "sample_alerts": alerts})


PORTFOLIO_TOOLS = [
    list_returns,
    list_refunds_awaiting_approval,
    list_open_investigation_cases,
    list_actions_for_return,
    get_monitoring_overview,
    summarize_returns,
]
