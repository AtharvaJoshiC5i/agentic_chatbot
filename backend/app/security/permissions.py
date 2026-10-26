"""Role-based permissions for API actions."""

from app.models.enums import UserRole

DEMO_LOGIN_ROLES = frozenset(
    {
        UserRole.RETURNS_ANALYST,
        UserRole.WAREHOUSE_MANAGER,
        UserRole.RETURNS_SUPERVISOR,
    }
)

READ_ROLES = DEMO_LOGIN_ROLES
WRITE_CASE_ROLES = frozenset(
    {
        UserRole.RETURNS_ANALYST,
        UserRole.RETURNS_SUPERVISOR,
    }
)
ASSIGN_CASE_ROLES = frozenset({UserRole.RETURNS_SUPERVISOR})
CASE_RESOLVE_ROLES = frozenset({UserRole.RETURNS_SUPERVISOR})
RETURN_CLOSE_ROLES = frozenset({UserRole.RETURNS_SUPERVISOR})
INSPECTION_WRITE_ROLES = frozenset(
    {
        UserRole.WAREHOUSE_MANAGER,
        UserRole.RETURNS_SUPERVISOR,
    }
)
REFUND_REQUEST_ROLES = frozenset(
    {
        UserRole.RETURNS_ANALYST,
        UserRole.RETURNS_SUPERVISOR,
    }
)
REFUND_APPROVE_ROLES = frozenset({UserRole.RETURNS_SUPERVISOR})
REFUND_EXECUTE_ROLES = frozenset({UserRole.RETURNS_SUPERVISOR})
RECOVERY_TASK_ROLES = frozenset(
    {
        UserRole.WAREHOUSE_MANAGER,
        UserRole.RETURNS_SUPERVISOR,
    }
)
ACTION_APPROVE_ROLES = frozenset({UserRole.RETURNS_SUPERVISOR})

# Persona handoff workflow (analyst -> warehouse -> analyst -> supervisor -> analyst)
VERDICT_ROLES = frozenset({UserRole.WAREHOUSE_MANAGER, UserRole.RETURNS_SUPERVISOR})
DECLINE_ROLES = frozenset({UserRole.RETURNS_ANALYST, UserRole.RETURNS_SUPERVISOR})
NOTIFICATION_SEND_ROLES = frozenset({UserRole.RETURNS_ANALYST, UserRole.RETURNS_SUPERVISOR})
REPLACEMENT_REQUEST_ROLES = frozenset({UserRole.RETURNS_ANALYST, UserRole.RETURNS_SUPERVISOR})
REPLACEMENT_DECIDE_ROLES = frozenset({UserRole.RETURNS_SUPERVISOR})
