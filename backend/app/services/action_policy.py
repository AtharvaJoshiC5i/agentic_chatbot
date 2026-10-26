"""Who may submit actions and which require supervisor approval (F7)."""

from app.models.enums import ActionType, UserRole
from app.security.permissions import (
    RECOVERY_TASK_ROLES,
    REFUND_EXECUTE_ROLES,
    REFUND_REQUEST_ROLES,
    WRITE_CASE_ROLES,
)

_SUBMIT_ROLES: dict[ActionType, frozenset[UserRole]] = {
    ActionType.CREATE_CASE: WRITE_CASE_ROLES,
    ActionType.ASSIGN_CASE: WRITE_CASE_ROLES,
    ActionType.REQUEST_REFUND: REFUND_REQUEST_ROLES,
    ActionType.EXECUTE_REFUND: REFUND_EXECUTE_ROLES,
    ActionType.CREATE_REPAIR_TASK: RECOVERY_TASK_ROLES,
    ActionType.CREATE_REFURBISHMENT_TASK: RECOVERY_TASK_ROLES,
    ActionType.CREATE_SUPPLIER_RETURN: RECOVERY_TASK_ROLES,
    ActionType.CREATE_RECYCLE_TASK: RECOVERY_TASK_ROLES,
    ActionType.CREATE_DISPOSE_TASK: RECOVERY_TASK_ROLES,
    ActionType.CREATE_INSPECTION_TASK: RECOVERY_TASK_ROLES,
    ActionType.CREATE_EVIDENCE_REQUEST: WRITE_CASE_ROLES,
    ActionType.CREATE_DATA_CORRECTION: WRITE_CASE_ROLES,
    ActionType.CREATE_WARRANTY_TASK: WRITE_CASE_ROLES,
    ActionType.CREATE_REPLACEMENT_REQUEST: REFUND_REQUEST_ROLES,
    ActionType.UPDATE_CASE_STATUS: WRITE_CASE_ROLES,
}


def can_submit(action_type: ActionType, role: UserRole) -> bool:
    allowed = _SUBMIT_ROLES.get(action_type)
    if allowed is None:
        return role == UserRole.ADMINISTRATOR
    return role in allowed


def requires_supervisor_approval(action_type: ActionType) -> bool:
    """Deterministic approval gate before execution."""
    # Refund and replacement requests are decided once, on the request itself, in the supervisor queue.
    return action_type in {
        ActionType.EXECUTE_REFUND,
        ActionType.CREATE_REPAIR_TASK,
        ActionType.CREATE_REFURBISHMENT_TASK,
        ActionType.CREATE_SUPPLIER_RETURN,
        ActionType.CREATE_RECYCLE_TASK,
        ActionType.CREATE_DISPOSE_TASK,
    }
