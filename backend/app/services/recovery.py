"""Product recovery task creation."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import ActorType, RecoveryMethod, SourceType, TaskStatus
from app.models.tables import RecoveryTask, Return
from app.security.deps import CurrentUser
from app.services.audit import record_audit
from app.services.recovery_optimizer import RecoveryOptimizerError, optimize_recovery
from app.services.return_events import record_return_event


class RecoveryServiceError(Exception):
    def __init__(self, message: str, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code


def create_recovery_task(
    session: Session,
    *,
    return_id: str,
    recovery_method: RecoveryMethod,
    assigned_to: str | None,
    actor: CurrentUser,
) -> RecoveryTask:
    if session.get(Return, return_id) is None:
        raise RecoveryServiceError("Return not found", "not_found")

    task = RecoveryTask(
        return_id=return_id,
        recovery_method=recovery_method.value,
        assigned_to=assigned_to,
        task_status=TaskStatus.PENDING.value,
        created_at=utc_now(),
        completed_at=None,
    )
    session.add(task)
    session.flush()
    record_return_event(
        session,
        return_id=return_id,
        event_type="recovery_task_created",
        description=f"Recovery task {task.recovery_task_id} ({recovery_method.value}).",
        source_type=SourceType.RECOVERY_TASK.value,
        source_id=str(task.recovery_task_id),
        event_timestamp=task.created_at,
    )
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="create_recovery_task",
        target_entity="recovery_task",
        target_id=str(task.recovery_task_id),
        execution_result="succeeded",
        evidence_references={"return_id": return_id, "method": recovery_method.value},
    )
    session.commit()
    session.refresh(task)
    return task


def create_task_from_recommendation(
    session: Session,
    *,
    return_id: str,
    assigned_to: str | None,
    actor: CurrentUser,
    allow_non_recommended: bool = False,
    recovery_method: RecoveryMethod | None = None,
) -> RecoveryTask:
    if session.get(Return, return_id) is None:
        raise RecoveryServiceError("Return not found", "not_found")
    recommendation = optimize_recovery(session, return_id)
    if recommendation.recommended_method is None:
        raise RecoveryServiceError("No eligible recovery recommendation", "no_recommendation")

    method_value = recommendation.recommended_method
    if recovery_method is not None:
        if not allow_non_recommended and recovery_method.value != method_value:
            raise RecoveryServiceError(
                "Requested method does not match optimizer recommendation",
                "method_mismatch",
            )
        method_value = recovery_method.value

    existing = session.execute(
        select(RecoveryTask).where(
            RecoveryTask.return_id == return_id,
            RecoveryTask.recovery_method == method_value,
            RecoveryTask.task_status.in_(
                [TaskStatus.PENDING.value, TaskStatus.ASSIGNED.value, TaskStatus.IN_PROGRESS.value]
            ),
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    return create_recovery_task(
        session,
        return_id=return_id,
        recovery_method=RecoveryMethod(method_value),
        assigned_to=assigned_to,
        actor=actor,
    )
