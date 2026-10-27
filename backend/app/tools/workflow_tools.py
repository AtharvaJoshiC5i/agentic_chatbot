"""Timeline, passport, and evidence workflow tools."""

from langchain_core.tools import tool

from app.agents.context import get_agent_db, get_agent_user
from app.models.enums import CaseStatus, InspectionResult, ProductCondition, TaskStatus
from app.security.permissions import (
    ACTION_APPROVE_ROLES,
    CASE_RESOLVE_ROLES,
    DECLINE_ROLES,
    INSPECTION_WRITE_ROLES,
    NOTIFICATION_SEND_ROLES,
    RECOVERY_TASK_ROLES,
    REPLACEMENT_DECIDE_ROLES,
    VERDICT_ROLES,
)
from app.services.handoff import WorkflowError, decline_return, record_verdict, verdict_to_dict
from app.services.notifications import NotificationError, list_notifications, notification_to_dict, send_notification
from app.services.replacements import ReplacementServiceError, decide_replacement, replacement_to_dict
from app.services.approvals import list_pending_approvals
from app.services.cases import CaseServiceError, transition_case_status
from app.services.inspections import InspectionServiceError, record_inspection
from app.services.return_status import ReturnStatusError, receive_return_at_warehouse
from app.services.warehouse_handoff import get_warehouse_handoff_status
from app.services.warehouse_queue import build_warehouse_work_queue
from app.services.recovery_tasks import RecoveryTaskServiceError, update_recovery_task
from app.investigation.evidence_summary import detect_return_inconsistencies
from app.services.complaint_intelligence import analyze_product_complaint_patterns
from app.services.timeline import build_return_timeline
from app.tools.compact import compact_json
from app.tools.workflow_response import current_workflow_handoff


@tool
def build_return_timeline_tool(return_id: str) -> str:
    """Construct source-backed chronological timeline for a return."""
    session = get_agent_db()
    events = build_return_timeline(session, return_id, sync=True)
    return compact_json({"return_id": return_id, "events": events})


@tool
def detect_return_inconsistencies_tool(return_id: str) -> str:
    """Explainable discrepancy checks — confirmed vs disputed vs missing evidence."""
    session = get_agent_db()
    return compact_json(detect_return_inconsistencies(session, return_id))


@tool
def analyze_product_complaint_patterns_tool(
    product_id: str | None = None,
    model_keyword: str | None = None,
) -> str:
    """Detect recurring complaint/return patterns for a product or model keyword."""
    session = get_agent_db()
    if not product_id and not model_keyword:
        return compact_json({"error": "invalid_request", "message": "Provide product_id or model_keyword"})
    result = analyze_product_complaint_patterns(session, product_id=product_id, model_keyword=model_keyword)
    return compact_json(result)


@tool
def get_warehouse_handoff_status_tool(return_id: str) -> str:
    """Warehouse: analyst case, receipt status, inspection count, and next step (receive vs inspect).

    Call this first for handoff returns. Never state 'no open case' if active_case is present."""
    session = get_agent_db()
    user = get_agent_user()
    if user.role not in INSPECTION_WRITE_ROLES:
        return compact_json({"error": "forbidden", "message": "Warehouse role required."})
    return compact_json(get_warehouse_handoff_status(session, return_id.upper()))


@tool
def list_warehouse_handoffs(limit: int = 25) -> str:
    """List returns in the warehouse inspection queue (analyst cases awaiting receipt or inspection)."""
    session = get_agent_db()
    user = get_agent_user()
    if user.role not in INSPECTION_WRITE_ROLES:
        return compact_json({"error": "forbidden", "message": "Warehouse role required."})
    items = build_warehouse_work_queue(session, limit=min(limit, 40))
    return compact_json({"count": len(items), "items": items})


@tool
def record_warehouse_receipt(return_id: str, arrival_confirmed: bool) -> str:
    """Record physical warehouse arrival only after a person explicitly confirms the unit is present."""
    session = get_agent_db()
    user = get_agent_user()
    if user.role not in INSPECTION_WRITE_ROLES:
        return compact_json({"error": "forbidden", "message": "Role cannot record warehouse receipt."})
    if not arrival_confirmed:
        return compact_json(
            {
                "error": "arrival_not_confirmed",
                "message": "Receipt was not recorded. Confirm that the physical unit is present at the warehouse first.",
            }
        )
    try:
        row = receive_return_at_warehouse(session, return_id, user)
    except ReturnStatusError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json(
        {
            "return_id": row.return_id,
            "return_status": row.return_status,
            "received_date": row.received_date.isoformat() if row.received_date else None,
            "workflow": current_workflow_handoff(session, row.return_id),
        }
    )


@tool
def record_inspection_tool(
    return_id: str,
    product_condition: str,
    inspection_result: str,
    returned_serial_number: str | None = None,
    accessories_complete: bool = True,
    defect_verified: bool = False,
    inspector_notes: str | None = None,
) -> str:
    """Record warehouse inspection after receipt. Required before analyst submits refund/replacement."""
    session = get_agent_db()
    user = get_agent_user()
    if user.role not in INSPECTION_WRITE_ROLES:
        return compact_json({"error": "forbidden", "message": "Role cannot record inspections."})
    try:
        row = record_inspection(
            session,
            return_id=return_id,
            product_condition=ProductCondition(product_condition.strip().lower()),
            returned_serial_number=returned_serial_number,
            accessories_complete=accessories_complete,
            defect_verified=defect_verified,
            inspection_result=InspectionResult(inspection_result.strip().lower()),
            inspector_notes=inspector_notes,
            actor=user,
        )
    except (InspectionServiceError, ValueError) as exc:
        code = getattr(exc, "code", "invalid_request")
        return compact_json({"error": code, "message": str(exc)})
    return compact_json(
        {
            "inspection_id": row.inspection_id,
            "return_id": row.return_id,
            "workflow": current_workflow_handoff(session, row.return_id),
        }
    )


@tool
def update_recovery_task_tool(
    task_id: int,
    assigned_to: str | None = None,
    task_status: str | None = None,
) -> str:
    """Assign or progress a recovery task (operations or supervisor)."""
    session = get_agent_db()
    user = get_agent_user()
    if user.role not in RECOVERY_TASK_ROLES:
        return compact_json({"error": "forbidden", "message": "Role cannot update recovery tasks."})
    status_enum = TaskStatus(task_status.strip().lower()) if task_status else None
    try:
        task = update_recovery_task(
            session,
            task_id,
            assigned_to=assigned_to,
            task_status=status_enum,
            actor=user,
        )
    except (RecoveryTaskServiceError, ValueError) as exc:
        code = getattr(exc, "code", "invalid_request")
        return compact_json({"error": code, "message": str(exc)})
    return compact_json(
        {
            "recovery_task_id": task.recovery_task_id,
            "task_status": task.task_status,
            "assigned_to": task.assigned_to,
        }
    )


@tool
def resolve_investigation_case(case_id: int, resolution_notes: str | None = None) -> str:
    """Mark an investigation case resolved (supervisor)."""
    session = get_agent_db()
    user = get_agent_user()
    if user.role not in CASE_RESOLVE_ROLES:
        return compact_json({"error": "forbidden", "message": "Only supervisors may resolve cases."})
    try:
        case = transition_case_status(
            session,
            case_id=case_id,
            new_status=CaseStatus.RESOLVED,
            actor=user,
            resolution_notes=resolution_notes,
        )
    except CaseServiceError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json({"case_id": case.case_id, "case_status": case.case_status})


@tool
def list_pending_approvals_tool(limit: int = 50) -> str:
    """List pending refund and action approvals (supervisor)."""
    session = get_agent_db()
    user = get_agent_user()
    if user.role not in ACTION_APPROVE_ROLES:
        return compact_json({"error": "forbidden", "message": "Only supervisors may view approvals."})
    return compact_json(list_pending_approvals(session, limit=limit))


@tool
def record_warehouse_verdict(return_id: str, feasible: bool, recommendation: str, notes: str = "") -> str:
    """Warehouse manager: say whether the customer's refund or replacement CAN be performed, after inspecting.
    recommendation is 'proceed' (feasible) or 'decline' (not feasible; notes must give the reason).
    The result goes back to the returns analyst, who then submits it or declines."""
    session = get_agent_db()
    user = get_agent_user()
    if user.role not in VERDICT_ROLES:
        return compact_json({"error": "forbidden", "message": "Only the warehouse manager or a supervisor gives the verdict."})
    try:
        verdict = record_verdict(
            session, return_id=return_id.strip().upper(), actor=user, feasible=feasible, recommendation=recommendation, notes=notes
        )
    except WorkflowError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json(
        {
            **verdict_to_dict(verdict),
            "next_owner": "returns_analyst",
            "workflow": current_workflow_handoff(session, verdict.return_id),
        }
    )


@tool
def decline_return_request(return_id: str, reason: str) -> str:
    """Returns analyst: decline only a definite policy failure before warehouse handoff or a request the warehouse
    found infeasible. Rejects the return and creates a customer message draft for analyst review."""
    session = get_agent_db()
    user = get_agent_user()
    if user.role not in DECLINE_ROLES:
        return compact_json({"error": "forbidden", "message": "Only the returns analyst or a supervisor may decline a request."})
    try:
        row = decline_return(session, return_id=return_id.strip().upper(), actor=user, reason=reason)
    except (WorkflowError, ReturnStatusError) as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json(
        {
            "return_id": row.return_id,
            "return_status": row.return_status,
            "next_step": "Review and confirm the customer message draft.",
            "workflow": current_workflow_handoff(session, row.return_id),
        }
    )


@tool
def decide_replacement_request(replacement_id: int, approve: bool, reason: str = "") -> str:
    """Supervisor: approve or reject a replacement request. A reason is required to reject.
    Approval reserves one unit of stock and resolves the return; the decision is handed to the analyst."""
    session = get_agent_db()
    user = get_agent_user()
    if user.role not in REPLACEMENT_DECIDE_ROLES:
        return compact_json({"error": "forbidden", "message": "Only supervisors decide replacements."})
    try:
        row = decide_replacement(session, replacement_id=replacement_id, actor=user, approve=approve, reason=reason)
    except ReplacementServiceError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json(
        {
            **replacement_to_dict(row),
            "workflow": current_workflow_handoff(session, row.return_id),
        }
    )


@tool
def list_customer_notifications(return_id: str = "", status: str = "draft") -> str:
    """List drafted (status=draft) or sent customer emails, optionally for one return."""
    session = get_agent_db()
    rows = list_notifications(session, status=status or None, return_id=return_id or None, limit=25)
    return compact_json({"count": len(rows), "notifications": [notification_to_dict(r) for r in rows]})


@tool
def send_customer_notification(notification_id: int, subject: str = "", body: str = "") -> str:
    """Returns analyst: confirm and send a drafted customer email (optionally with an edited subject or body).
    Only call after the user has confirmed. This closes the case and the return."""
    session = get_agent_db()
    user = get_agent_user()
    if user.role not in NOTIFICATION_SEND_ROLES:
        return compact_json({"error": "forbidden", "message": "Only the returns analyst or a supervisor sends customer emails."})
    try:
        note = send_notification(session, notification_id=notification_id, actor=user, subject=subject or None, body=body or None)
    except NotificationError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json(
        {
            **notification_to_dict(note),
            "workflow": current_workflow_handoff(session, note.return_id),
            "delivery_note": "Confirmation recorded locally; no email was delivered.",
        }
    )


WORKFLOW_TOOLS = [
    build_return_timeline_tool,
    detect_return_inconsistencies_tool,
    analyze_product_complaint_patterns_tool,
    get_warehouse_handoff_status_tool,
    list_warehouse_handoffs,
    record_warehouse_receipt,
    record_inspection_tool,
    update_recovery_task_tool,
    resolve_investigation_case,
    list_pending_approvals_tool,
    record_warehouse_verdict,
    decline_return_request,
    decide_replacement_request,
    list_customer_notifications,
    send_customer_notification,
]
