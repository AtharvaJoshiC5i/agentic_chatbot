"""Role-based LangGraph tool binding."""

from langchain_core.tools import BaseTool

from app.models.enums import UserRole
from app.security.permissions import (
    ACTION_APPROVE_ROLES,
    ASSIGN_CASE_ROLES,
    CASE_RESOLVE_ROLES,
    DECLINE_ROLES,
    NOTIFICATION_SEND_ROLES,
    REPLACEMENT_DECIDE_ROLES,
    VERDICT_ROLES,
    INSPECTION_WRITE_ROLES,
    RECOVERY_TASK_ROLES,
    REFUND_APPROVE_ROLES,
    REFUND_EXECUTE_ROLES,
    REFUND_REQUEST_ROLES,
    WRITE_CASE_ROLES,
)

_TOOL_ROLE_REQUIREMENTS: dict[str, frozenset[UserRole]] = {
    "submit_create_investigation_case": WRITE_CASE_ROLES,
    "submit_refund_request": REFUND_REQUEST_ROLES,
    "submit_replacement_request": REFUND_REQUEST_ROLES,
    "submit_repair_recovery_task": RECOVERY_TASK_ROLES,
    "submit_refurbishment_task": RECOVERY_TASK_ROLES,
    "submit_inspection_task": RECOVERY_TASK_ROLES,
    "submit_supplier_return_task": RECOVERY_TASK_ROLES,
    "submit_recycle_task": RECOVERY_TASK_ROLES,
    "submit_evidence_request": WRITE_CASE_ROLES,
    "approve_action_request": ACTION_APPROVE_ROLES,
    "get_warehouse_handoff_status_tool": INSPECTION_WRITE_ROLES,
    "list_warehouse_handoffs": INSPECTION_WRITE_ROLES,
    "record_warehouse_receipt": INSPECTION_WRITE_ROLES,
    "record_inspection_tool": INSPECTION_WRITE_ROLES,
    "update_recovery_task_tool": RECOVERY_TASK_ROLES,
    "resolve_investigation_case": CASE_RESOLVE_ROLES,
    "list_pending_approvals_tool": ACTION_APPROVE_ROLES,
    "approve_refund_record": REFUND_APPROVE_ROLES,
    "execute_refund_payout": REFUND_EXECUTE_ROLES,
    "assign_investigation_case": ASSIGN_CASE_ROLES,
    "execute_action_request": REFUND_EXECUTE_ROLES | RECOVERY_TASK_ROLES,
    "record_warehouse_verdict": VERDICT_ROLES,
    "decline_return_request": DECLINE_ROLES,
    "decide_replacement_request": REPLACEMENT_DECIDE_ROLES,
    "send_customer_notification": NOTIFICATION_SEND_ROLES,
}


def filter_tools_for_role(tools: list[BaseTool], role: UserRole | None) -> list[BaseTool]:
    if role is None:
        return tools
    filtered: list[BaseTool] = []
    for tool in tools:
        required = _TOOL_ROLE_REQUIREMENTS.get(tool.name)
        if required is None or role in required:
            filtered.append(tool)
    return filtered
