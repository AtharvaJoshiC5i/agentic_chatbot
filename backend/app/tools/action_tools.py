"""LangGraph tools for the F7 action lifecycle (submit / status / execute)."""

import json
import uuid

from langchain_core.tools import tool

from app.agents.context import get_agent_db, get_agent_user
from app.models.enums import ActionType, ActorType
from app.security.permissions import ASSIGN_CASE_ROLES
from app.security.permissions import REFUND_APPROVE_ROLES, REFUND_EXECUTE_ROLES
from app.services.actions import ActionServiceError, approve_action, execute_action, get_action, submit_action
from app.services.refunds import RefundServiceError, approve_refund, execute_refund
from app.services.cases import CaseServiceError, assign_case
from app.services.issue_types import coerce_issue_type
from app.tools.compact import compact_json


@tool
def submit_create_investigation_case(
    return_id: str,
    issue_type: str,
    priority: str = "medium",
    idempotency_key: str = "",
) -> str:
    """Submit create_case (executes immediately when policy allows).

    issue_type must be a canonical enum (serial_mismatch, missing_inspection, general, etc.).
    If inspection is missing, use missing_inspection — not inspection_needed or defective_product.
    """
    session = get_agent_db()
    user = get_agent_user()
    try:
        normalized = coerce_issue_type(issue_type).value
    except CaseServiceError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    key = idempotency_key or f"agent-case-{return_id}-{normalized}"
    try:
        action = submit_action(
            session,
            action_type=ActionType.CREATE_CASE,
            return_id=return_id,
            payload={"issue_type": normalized, "priority": priority},
            idempotency_key=key,
            actor=user,
            actor_type=ActorType.AGENT,
        )
    except ActionServiceError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json(
        {
            "action_id": action.action_id,
            "action_type": action.action_type,
            "approval_status": action.approval_status,
            "execution_status": action.execution_status,
        }
    )


@tool
def submit_refund_request(
    return_id: str,
    refund_amount_paise: int,
    idempotency_key: str = "",
) -> str:
    """Submit refund request (supervisor approval required before execution).

    Call calculate_refundable_amount and get_inspection_results on this return in the
    same conversation before submitting. Use remaining_refundable_paise from calculate_refundable_amount.
    """
    session = get_agent_db()
    user = get_agent_user()
    refund_key = idempotency_key.strip() or f"agent-refund-{return_id}-{uuid.uuid4().hex[:12]}"
    try:
        action = submit_action(
            session,
            action_type=ActionType.REQUEST_REFUND,
            return_id=return_id,
            payload={
                "return_id": return_id,
                "refund_amount_paise": refund_amount_paise,
                "refund_idempotency_key": refund_key,
            },
            idempotency_key=f"action-refund-{refund_key}",
            actor=user,
            actor_type=ActorType.AGENT,
        )
    except ActionServiceError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json(
        {
            "action_id": action.action_id,
            "approval_required": action.approval_required,
            "approval_status": action.approval_status,
            "execution_status": action.execution_status,
            "next_step": "Supervisor approval completes payout automatically when amount is within policy.",
        }
    )


@tool
def submit_replacement_request(return_id: str, idempotency_key: str = "") -> str:
    """Submit replacement request (supervisor approval required before dispatch).

    Call get_inspection_results and get_return_details first. Use when requested_resolution
    is replacement and warehouse inspection supports the claim.
    """
    session = get_agent_db()
    user = get_agent_user()
    key = idempotency_key.strip() or f"agent-replacement-{return_id}-{uuid.uuid4().hex[:12]}"
    try:
        action = submit_action(
            session,
            action_type=ActionType.CREATE_REPLACEMENT_REQUEST,
            return_id=return_id,
            payload={"return_id": return_id},
            idempotency_key=f"action-replacement-{key}",
            actor=user,
            actor_type=ActorType.AGENT,
        )
    except ActionServiceError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json(
        {
            "action_id": action.action_id,
            "approval_required": action.approval_required,
            "approval_status": action.approval_status,
            "execution_status": action.execution_status,
            "next_step": "Supervisor must approve before replacement is dispatched.",
        }
    )


@tool
def submit_repair_recovery_task(return_id: str, assigned_to: str | None = None, idempotency_key: str = "") -> str:
    """Submit repair-and-resell recovery task (approval required)."""
    session = get_agent_db()
    user = get_agent_user()
    key = idempotency_key or f"agent-repair-{return_id}"
    try:
        action = submit_action(
            session,
            action_type=ActionType.CREATE_REPAIR_TASK,
            return_id=return_id,
            payload={"return_id": return_id, "assigned_to": assigned_to},
            idempotency_key=key,
            actor=user,
            actor_type=ActorType.AGENT,
        )
    except ActionServiceError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json(
        {
            "action_id": action.action_id,
            "approval_status": action.approval_status,
            "execution_status": action.execution_status,
        }
    )


@tool
def get_action_request_status(action_id: int) -> str:
    """Fetch action request approval and execution status."""
    session = get_agent_db()
    action = get_action(session, action_id)
    if action is None:
        return compact_json({"error": "not_found", "action_id": action_id})
    return compact_json(
        {
            "action_id": action.action_id,
            "return_id": action.return_id,
            "action_type": action.action_type,
            "approval_required": action.approval_required,
            "approval_status": action.approval_status,
            "execution_status": action.execution_status,
            "requested_by": action.requested_by,
        }
    )


@tool
def approve_refund_record(refund_id: int, approve: bool = True, reason: str = "") -> str:
    """Approve or reject a refund (supervisor). Approving pays the refund out and resolves the return; rejecting needs a reason. Replaces the payout step. Use before payout if needed."""
    session = get_agent_db()
    user = get_agent_user()
    if user.role not in REFUND_APPROVE_ROLES:
        return compact_json({"error": "forbidden", "message": "Only supervisors may approve refunds."})
    try:
        refund = approve_refund(session, refund_id, user, approve=approve, reason=reason or None)
    except RefundServiceError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json(
        {
            "refund_id": refund.refund_id,
            "return_id": refund.return_id,
            "refund_status": refund.refund_status,
            "approval_status": refund.approval_status,
        }
    )


@tool
def execute_refund_payout(refund_id: int) -> str:
    """Complete customer payout for an approved refund (supervisor or admin)."""
    session = get_agent_db()
    user = get_agent_user()
    if user.role not in REFUND_EXECUTE_ROLES:
        return compact_json({"error": "forbidden", "message": "Only supervisors may execute refunds."})
    try:
        refund = execute_refund(session, refund_id, user)
    except RefundServiceError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json(
        {
            "refund_id": refund.refund_id,
            "return_id": refund.return_id,
            "refund_status": refund.refund_status,
            "processed_date": str(refund.processed_date) if refund.processed_date else None,
        }
    )


@tool
def execute_action_request(action_id: int) -> str:
    """Run an approved action (refund request, repair task, execute refund, etc.)."""
    session = get_agent_db()
    user = get_agent_user()
    try:
        action = execute_action(session, action_id, user, actor_type=ActorType.AGENT)
    except ActionServiceError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    payload: dict[str, object] = {}
    if action.payload_json:
        try:
            payload = json.loads(action.payload_json)
        except json.JSONDecodeError:
            payload = {}
    return compact_json(
        {
            "action_id": action.action_id,
            "execution_status": action.execution_status,
            "executed_at": action.executed_at,
            "refund_id": payload.get("refund_id"),
            "refund_status": payload.get("refund_status"),
        }
    )


def _submit_task(action_type: ActionType, return_id: str, assigned_to: str | None, key: str) -> str:
    session = get_agent_db()
    user = get_agent_user()
    try:
        action = submit_action(
            session,
            action_type=action_type,
            return_id=return_id,
            payload={"return_id": return_id, "assigned_to": assigned_to},
            idempotency_key=key,
            actor=user,
            actor_type=ActorType.AGENT,
        )
    except ActionServiceError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json(
        {"action_id": action.action_id, "action_type": action.action_type,
         "approval_status": action.approval_status, "execution_status": action.execution_status}
    )


@tool
def submit_refurbishment_task(return_id: str, assigned_to: str | None = None, idempotency_key: str = "") -> str:
    """Submit a refurbish-and-resell recovery task (approval required). Warehouse manager, supervisor or admin."""
    return _submit_task(ActionType.CREATE_REFURBISHMENT_TASK, return_id, assigned_to, idempotency_key or f"agent-refurb-{return_id}")


@tool
def submit_inspection_task(return_id: str, assigned_to: str | None = None, idempotency_key: str = "") -> str:
    """Request a warehouse inspection task, e.g. when a received return has no inspection. Warehouse manager, supervisor or admin."""
    return _submit_task(ActionType.CREATE_INSPECTION_TASK, return_id, assigned_to, idempotency_key or f"agent-inspect-{return_id}")


@tool
def approve_action_request(action_id: int, approve: bool = True) -> str:
    """Approve (or reject with approve=false) an action awaiting supervisor approval. Supervisor only."""
    session = get_agent_db()
    user = get_agent_user()
    try:
        action = approve_action(session, action_id, user, approve=approve)
    except ActionServiceError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json(
        {"action_id": action.action_id, "approval_status": action.approval_status, "execution_status": action.execution_status}
    )


@tool
def approve_refund_request(action_id: int, approve: bool = True) -> str:
    """Approve or reject a pending refund action request (supervisor). Completes payout when approved."""
    session = get_agent_db()
    user = get_agent_user()
    try:
        action = approve_action(session, action_id, user, approve=approve)
    except ActionServiceError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json(
        {"action_id": action.action_id, "approval_status": action.approval_status, "execution_status": action.execution_status}
    )


@tool
def assign_investigation_case(case_id: int, assigned_to: str) -> str:
    """Assign an investigation case to an analyst username (e.g. analyst_02). Supervisor or admin only."""
    session = get_agent_db()
    user = get_agent_user()
    if user.role not in ASSIGN_CASE_ROLES:
        return compact_json({"error": "forbidden", "message": "Only supervisors or administrators may assign cases."})
    try:
        case = assign_case(session, case_id, assigned_to, user)
        session.commit()
    except CaseServiceError as exc:
        return compact_json({"error": getattr(exc, "code", "error"), "message": str(exc)})
    return compact_json({"case_id": case.case_id, "assigned_to": case.assigned_to, "status": case.case_status})


@tool
def submit_supplier_return_task(return_id: str, assigned_to: str | None = None, idempotency_key: str = "") -> str:
    """Submit supplier-return recovery task (approval required)."""
    return _submit_task(ActionType.CREATE_SUPPLIER_RETURN, return_id, assigned_to, idempotency_key or f"agent-supplier-{return_id}")


@tool
def submit_recycle_task(return_id: str, assigned_to: str | None = None, idempotency_key: str = "") -> str:
    """Submit recycling disposition task (approval required)."""
    return _submit_task(ActionType.CREATE_RECYCLE_TASK, return_id, assigned_to, idempotency_key or f"agent-recycle-{return_id}")


@tool
def submit_evidence_request(
    return_id: str,
    request_type: str,
    description: str,
    idempotency_key: str = "",
) -> str:
    """Request additional verification evidence (executes immediately)."""
    session = get_agent_db()
    user = get_agent_user()
    key = idempotency_key or f"agent-evidence-{return_id}-{request_type}"
    try:
        action = submit_action(
            session,
            action_type=ActionType.CREATE_EVIDENCE_REQUEST,
            return_id=return_id,
            payload={
                "return_id": return_id,
                "request_type": request_type,
                "description": description,
            },
            idempotency_key=key,
            actor=user,
            actor_type=ActorType.AGENT,
        )
    except ActionServiceError as exc:
        return compact_json({"error": exc.code, "message": str(exc)})
    return compact_json(
        {
            "action_id": action.action_id,
            "execution_status": action.execution_status,
        }
    )


ACTION_TOOLS = [
    submit_create_investigation_case,
    submit_refund_request,
    submit_replacement_request,
    approve_refund_request,
    submit_repair_recovery_task,
    get_action_request_status,
    execute_action_request,
    approve_refund_record,
    execute_refund_payout,
    submit_refurbishment_task,
    submit_inspection_task,
    submit_supplier_return_task,
    submit_recycle_task,
    submit_evidence_request,
    approve_action_request,
    assign_investigation_case,
]
