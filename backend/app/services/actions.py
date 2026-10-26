"""Action request lifecycle: submit → approve → execute (F7)."""

import json
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.base import as_utc, utc_now
from app.models.enums import (
    ActionType,
    ActorType,
    ApprovalStatus,
    CaseStatus,
    ExecutionStatus,
    InventoryDispositionStatus,
    IssueType,
    RecoveryMethod,
    RefundStatus,
    SourceType,
    UserRole,
)
from app.models.tables import ActionRequest, Refund, Return
from app.security.deps import CurrentUser
from app.security.permissions import REFUND_EXECUTE_ROLES
from app.services.action_policy import can_submit, requires_supervisor_approval
from app.services.audit import record_audit
from app.services.cases import CaseServiceError, create_case, transition_case_status
from app.services.return_status import ReturnStatusError
from app.services.issue_types import coerce_issue_type
from app.services.evidence_requests import EvidenceRequestError, create_evidence_request
from app.services.inventory import InventoryServiceError, reserve_disposition
from app.services.recovery import RecoveryServiceError, create_recovery_task
from app.services.refunds import RefundServiceError, approve_refund, execute_refund, request_refund
from app.services.return_status import REFUND_AUTO_PAYOUT_MAX_PAISE
from app.services.replacements import ReplacementServiceError, create_replacement_request
from app.services.return_events import record_return_event
from app.services.warranty import WarrantyServiceError, create_warranty_claim


class ActionServiceError(Exception):
    def __init__(self, message: str, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code


def _ensure_actions_enabled() -> None:
    if get_settings().actions_disabled:
        raise ActionServiceError("Action execution is disabled (read-only mode).", "actions_disabled")


def _reject_if_approval_expired(session: Session, action: ActionRequest) -> None:
    if not action.approval_expires_at:
        return
    expires = as_utc(action.approval_expires_at)
    if expires is None:
        return
    if utc_now() <= expires:
        return
    action.approval_status = ApprovalStatus.REJECTED.value
    action.execution_status = ExecutionStatus.REJECTED.value
    session.commit()
    raise ActionServiceError("Approval has expired.", "approval_expired")


def _try_complete_refund_request(
    session: Session,
    action: ActionRequest,
    actor: CurrentUser,
) -> None:
    """After supervisor approves a refund request action, approve and pay out when allowed."""
    payload = _payload_dict(action)
    raw_id = payload.get("refund_id")
    if raw_id is None:
        return
    refund = session.get(Refund, int(raw_id))
    if refund is None:
        return
    if refund.refund_status == RefundStatus.COMPLETED.value:
        action.execution_status = ExecutionStatus.SUCCEEDED.value
        action.executed_at = utc_now()
        return
    if refund.refund_amount > REFUND_AUTO_PAYOUT_MAX_PAISE:
        if refund.approval_status != ApprovalStatus.APPROVED.value:
            approve_refund(session, refund.refund_id, actor, approve=True)
        action.execution_status = ExecutionStatus.APPROVED.value
        return
    if refund.approval_status != ApprovalStatus.APPROVED.value:
        approve_refund(session, refund.refund_id, actor, approve=True)
    if refund.refund_status != RefundStatus.COMPLETED.value:
        execute_refund(session, refund.refund_id, actor)
    action.execution_status = ExecutionStatus.SUCCEEDED.value
    action.executed_at = utc_now()
    payload = {**payload, "refund_id": refund.refund_id, "refund_status": RefundStatus.COMPLETED.value}
    action.payload_json = json.dumps(payload)


def _payload_dict(action: ActionRequest) -> dict[str, Any]:
    try:
        return json.loads(action.payload_json or "{}")
    except json.JSONDecodeError:
        return {}


def get_action(session: Session, action_id: int) -> ActionRequest | None:
    return session.get(ActionRequest, action_id)


def list_actions_for_return(session: Session, return_id: str, limit: int = 50) -> list[ActionRequest]:
    return list_actions(
        session, return_id=return_id, approval_status=None, execution_status=None, limit=limit
    )


def list_actions(
    session: Session,
    *,
    return_id: str | None = None,
    approval_status: str | None = None,
    execution_status: str | None = None,
    limit: int = 100,
) -> list[ActionRequest]:
    query = select(ActionRequest).order_by(ActionRequest.action_id.desc())
    if return_id:
        query = query.where(ActionRequest.return_id == return_id.strip().upper())
    if approval_status:
        query = query.where(ActionRequest.approval_status == approval_status.strip().lower())
    if execution_status:
        query = query.where(ActionRequest.execution_status == execution_status.strip().lower())
    return list(session.execute(query.limit(limit)).scalars().all())


def count_pending_actions(session: Session) -> int:
    return int(
        session.execute(
            select(func.count())
            .select_from(ActionRequest)
            .where(ActionRequest.approval_status == ApprovalStatus.PENDING.value)
        ).scalar_one()
    )


def submit_action(
    session: Session,
    *,
    action_type: ActionType,
    return_id: str | None,
    payload: dict[str, Any],
    idempotency_key: str,
    actor: CurrentUser,
    actor_type: ActorType = ActorType.USER,
    auto_execute: bool = True,
) -> ActionRequest:
    _ensure_actions_enabled()
    if not idempotency_key or len(idempotency_key) < 8:
        raise ActionServiceError("idempotency_key must be at least 8 characters")

    existing = session.execute(
        select(ActionRequest).where(ActionRequest.idempotency_key == idempotency_key)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    if return_id and session.get(Return, return_id) is None:
        raise ActionServiceError("Return not found", "not_found")

    if not can_submit(action_type, actor.role):
        raise ActionServiceError("Role cannot submit this action type", "forbidden")

    if action_type == ActionType.REQUEST_REFUND and return_id:
        completed = session.execute(
            select(Refund.refund_id).where(
                Refund.return_id == return_id, Refund.refund_status == RefundStatus.COMPLETED
            )
        ).first()
        if completed is not None:
            raise ActionServiceError(
                "A completed refund already exists for this return.", "duplicate_refund"
            )
        open_refund = session.execute(
            select(Refund.refund_id).where(
                Refund.return_id == return_id,
                Refund.refund_status.notin_(
                    (RefundStatus.COMPLETED, RefundStatus.CANCELLED)
                ),
            )
        ).first()
        if open_refund is not None:
            raise ActionServiceError(
                "An open refund already exists for this return. A supervisor must approve "
                "and execute payout on the existing refund before submitting another request.",
                "duplicate_refund_pending",
            )
        pending_action = session.execute(
            select(ActionRequest.action_id).where(
                ActionRequest.return_id == return_id,
                ActionRequest.action_type == ActionType.REQUEST_REFUND.value,
                ActionRequest.approval_status == ApprovalStatus.PENDING.value,
            )
        ).first()
        if pending_action is not None:
            raise ActionServiceError(
                "A refund request action is already awaiting supervisor approval for this return.",
                "duplicate_refund_action_pending",
            )

    needs_approval = requires_supervisor_approval(action_type)
    approval_status = ApprovalStatus.PENDING if needs_approval else ApprovalStatus.NOT_REQUIRED
    execution_status = (
        ExecutionStatus.AWAITING_APPROVAL if needs_approval else ExecutionStatus.PENDING
    )

    settings = get_settings()
    expires_at = None
    if needs_approval:
        expires_at = utc_now() + timedelta(hours=settings.action_approval_expire_hours)

    action = ActionRequest(
        return_id=return_id,
        action_type=action_type.value,
        requested_by=actor.username,
        approval_required=needs_approval,
        approval_status=approval_status.value,
        execution_status=execution_status.value,
        created_at=utc_now(),
        executed_at=None,
        approval_expires_at=expires_at,
        idempotency_key=idempotency_key,
        payload_json=json.dumps(payload),
    )
    session.add(action)
    session.flush()

    record_audit(
        session,
        actor=actor,
        actor_type=actor_type,
        action_type="submit_action",
        target_entity="action_request",
        target_id=str(action.action_id),
        execution_result="submitted",
        evidence_references={"action_type": action_type.value, "return_id": return_id, **payload},
    )

    if action_type == ActionType.REQUEST_REFUND and needs_approval:
        session.commit()
        refund = request_refund(
            session,
            return_id=return_id or str(payload.get("return_id")),
            refund_amount_paise=int(payload["refund_amount_paise"]),
            idempotency_key=str(payload.get("refund_idempotency_key", idempotency_key)),
            actor=actor,
        )
        merged = {
            **payload,
            "refund_id": refund.refund_id,
            "refund_status": refund.refund_status,
        }
        action.payload_json = json.dumps(merged)
        session.add(action)
        session.commit()
    elif not needs_approval and auto_execute:
        _execute_action_body(session, action, actor, actor_type=actor_type)
    else:
        session.commit()

    session.refresh(action)
    return action


def approve_action(
    session: Session,
    action_id: int,
    actor: CurrentUser,
    approve: bool = True,
) -> ActionRequest:
    action = session.get(ActionRequest, action_id)
    if action is None:
        raise ActionServiceError("Action not found", "not_found")
    if not action.approval_required:
        raise ActionServiceError("Action does not require approval")
    if action.approval_status != ApprovalStatus.PENDING.value:
        raise ActionServiceError("Action is not pending approval")

    _reject_if_approval_expired(session, action)

    if actor.role not in {UserRole.RETURNS_SUPERVISOR, UserRole.ADMINISTRATOR}:
        raise ActionServiceError("Only supervisors may approve actions", "forbidden")

    if approve:
        action.approval_status = ApprovalStatus.APPROVED.value
        action.execution_status = ExecutionStatus.APPROVED.value
        result = "approved"
    else:
        action.approval_status = ApprovalStatus.REJECTED.value
        action.execution_status = ExecutionStatus.REJECTED.value
        result = "rejected"

    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="approve_action",
        target_entity="action_request",
        target_id=str(action.action_id),
        execution_result=result,
    )
    if approve and action.action_type == ActionType.REQUEST_REFUND.value:
        _try_complete_refund_request(session, action, actor)
    session.commit()
    session.refresh(action)
    if (
        approve
        and action.approval_status == ApprovalStatus.APPROVED.value
        and action.action_type == ActionType.CREATE_REPLACEMENT_REQUEST.value
        and action.execution_status == ExecutionStatus.APPROVED.value
    ):
        try:
            execute_action(session, action.action_id, actor, actor_type=ActorType.USER)
        except ActionServiceError:
            pass
        session.refresh(action)
    return action


def execute_action(
    session: Session,
    action_id: int,
    actor: CurrentUser,
    actor_type: ActorType = ActorType.USER,
) -> ActionRequest:
    _ensure_actions_enabled()
    action = session.get(ActionRequest, action_id)
    if action is None:
        raise ActionServiceError("Action not found", "not_found")

    if action.execution_status in {
        ExecutionStatus.SUCCEEDED.value,
        ExecutionStatus.FAILED.value,
        ExecutionStatus.REJECTED.value,
        ExecutionStatus.CANCELLED.value,
    }:
        raise ActionServiceError("Action is already in a terminal state")

    if action.approval_required and action.approval_status != ApprovalStatus.APPROVED.value:
        raise ActionServiceError("Action must be approved before execution")

    _reject_if_approval_expired(session, action)

    action_type = ActionType(action.action_type)
    if not can_submit(action_type, actor.role):
        raise ActionServiceError("Role cannot execute this action type", "forbidden")

    _execute_action_body(session, action, actor, actor_type=actor_type)
    session.refresh(action)
    return action


def _execute_action_body(
    session: Session,
    action: ActionRequest,
    actor: CurrentUser,
    *,
    actor_type: ActorType,
) -> None:
    action.execution_status = ExecutionStatus.EXECUTING.value
    session.flush()
    payload = _payload_dict(action)
    action_type = ActionType(action.action_type)

    try:
        if action_type == ActionType.CREATE_CASE:
            create_case(
                session,
                return_id=action.return_id or payload["return_id"],
                issue_type=coerce_issue_type(str(payload.get("issue_type", IssueType.GENERAL.value))),
                priority=str(payload.get("priority", "medium")),
                actor=actor,
            )
        elif action_type == ActionType.REQUEST_REFUND:
            existing_id = payload.get("refund_id")
            if existing_id:
                refund = session.get(Refund, int(existing_id))
                if refund is None:
                    raise ActionServiceError("Linked refund not found", "not_found")
                if refund.refund_status != RefundStatus.COMPLETED.value:
                    _try_complete_refund_request(session, action, actor)
            else:
                refund = request_refund(
                    session,
                    return_id=action.return_id or payload["return_id"],
                    refund_amount_paise=int(payload["refund_amount_paise"]),
                    idempotency_key=str(payload.get("refund_idempotency_key", action.idempotency_key)),
                    actor=actor,
                )
                _try_complete_refund_request(session, action, actor)
            refund = session.get(Refund, int(_payload_dict(action).get("refund_id", refund.refund_id)))
            if refund:
                payload = {
                    **payload,
                    "refund_id": refund.refund_id,
                    "refund_status": refund.refund_status,
                }
                action.payload_json = json.dumps(payload)
        elif action_type == ActionType.EXECUTE_REFUND:
            refund_id = int(payload["refund_id"])
            execute_refund(session, refund_id, actor)
        elif action_type == ActionType.CREATE_REPAIR_TASK:
            create_recovery_task(
                session,
                return_id=action.return_id or payload["return_id"],
                recovery_method=RecoveryMethod.REPAIR_RESELL,
                assigned_to=payload.get("assigned_to"),
                actor=actor,
            )
        elif action_type == ActionType.CREATE_REFURBISHMENT_TASK:
            create_recovery_task(
                session,
                return_id=action.return_id or payload["return_id"],
                recovery_method=RecoveryMethod.REFURBISH_RESELL,
                assigned_to=payload.get("assigned_to"),
                actor=actor,
            )
        elif action_type == ActionType.CREATE_INSPECTION_TASK:
            if action.return_id:
                record_return_event(
                    session,
                    return_id=action.return_id,
                    event_type="other",
                    description="Inspection task requested via action workflow.",
                    source_type=SourceType.SYSTEM.value,
                    source_id=f"action:{action.action_id}",
                )
        elif action_type in {
            ActionType.CREATE_SUPPLIER_RETURN,
            ActionType.CREATE_RECYCLE_TASK,
            ActionType.CREATE_DISPOSE_TASK,
        }:
            method_map = {
                ActionType.CREATE_SUPPLIER_RETURN: RecoveryMethod.SUPPLIER_RETURN,
                ActionType.CREATE_RECYCLE_TASK: RecoveryMethod.RECYCLE,
                ActionType.CREATE_DISPOSE_TASK: RecoveryMethod.DISPOSE,
            }
            method = method_map[action_type]
            task = create_recovery_task(
                session,
                return_id=action.return_id or payload["return_id"],
                recovery_method=method,
                assigned_to=payload.get("assigned_to"),
                actor=actor,
            )
            disposition_map = {
                RecoveryMethod.SUPPLIER_RETURN: InventoryDispositionStatus.SUPPLIER_RETURN,
                RecoveryMethod.RECYCLE: InventoryDispositionStatus.RECYCLED,
                RecoveryMethod.DISPOSE: InventoryDispositionStatus.DISPOSED,
            }
            reserve_disposition(
                session,
                return_id=task.return_id,
                disposition=disposition_map[method],
                recovery_task_id=task.recovery_task_id,
            )
        elif action_type == ActionType.CREATE_EVIDENCE_REQUEST:
            create_evidence_request(
                session,
                return_id=action.return_id or payload["return_id"],
                request_type=str(payload.get("request_type", "verification")),
                description=str(payload.get("description", "Additional evidence required.")),
                actor=actor,
                case_id=payload.get("case_id"),
            )
        elif action_type == ActionType.CREATE_DATA_CORRECTION:
            create_evidence_request(
                session,
                return_id=action.return_id or payload["return_id"],
                request_type="data_correction",
                description=str(payload.get("description", "Authorized data correction requested.")),
                actor=actor,
                case_id=payload.get("case_id"),
            )
        elif action_type == ActionType.CREATE_WARRANTY_TASK:
            create_warranty_claim(
                session,
                return_id=action.return_id or payload["return_id"],
                notes=payload.get("notes"),
                actor=actor,
            )
        elif action_type == ActionType.CREATE_REPLACEMENT_REQUEST:
            rep = create_replacement_request(
                session,
                return_id=action.return_id or payload["return_id"],
                actor=actor,
            )
            payload = {**payload, "replacement_id": rep.replacement_id, "replacement_status": rep.status}
            action.payload_json = json.dumps(payload)
        elif action_type == ActionType.UPDATE_CASE_STATUS:
            transition_case_status(
                session,
                case_id=int(payload["case_id"]),
                new_status=CaseStatus(str(payload["new_status"])),
                actor=actor,
                resolution_notes=payload.get("resolution_notes"),
            )
        else:
            raise ActionServiceError(f"Unsupported action type: {action_type.value}")

        action.execution_status = ExecutionStatus.SUCCEEDED.value
        action.executed_at = utc_now()
        if not action.approval_required:
            action.approval_status = ApprovalStatus.NOT_REQUIRED.value

        record_audit(
            session,
            actor=actor,
            actor_type=actor_type,
            action_type="execute_action",
            target_entity="action_request",
            target_id=str(action.action_id),
            execution_result="succeeded",
        )
        session.commit()
    except ReturnStatusError as exc:
        action.execution_status = ExecutionStatus.FAILED.value
        action.executed_at = utc_now()
        record_audit(
            session,
            actor=actor,
            actor_type=actor_type,
            action_type="execute_action",
            target_entity="action_request",
            target_id=str(action.action_id),
            execution_result="failed",
            evidence_references={"error": str(exc), "code": exc.code},
        )
        session.commit()
        raise ActionServiceError(str(exc), exc.code) from exc
    except (
        CaseServiceError,
        RefundServiceError,
        RecoveryServiceError,
        ActionServiceError,
        EvidenceRequestError,
        ReplacementServiceError,
        WarrantyServiceError,
        InventoryServiceError,
    ) as exc:
        action.execution_status = ExecutionStatus.FAILED.value
        action.executed_at = utc_now()
        record_audit(
            session,
            actor=actor,
            actor_type=actor_type,
            action_type="execute_action",
            target_entity="action_request",
            target_id=str(action.action_id),
            execution_result="failed",
            evidence_references={"error": str(exc), "code": getattr(exc, "code", "error")},
        )
        session.commit()
        raise ActionServiceError(str(exc), getattr(exc, "code", "execution_failed")) from exc


def mark_action_executed(session: Session, action_id: int, succeeded: bool = True) -> ActionRequest:
    """Legacy helper — prefer execute_action."""
    action = session.get(ActionRequest, action_id)
    if action is None:
        raise ActionServiceError("Action not found", "not_found")
    action.execution_status = ExecutionStatus.SUCCEEDED.value if succeeded else ExecutionStatus.FAILED.value
    action.executed_at = utc_now()
    session.commit()
    session.refresh(action)
    return action
