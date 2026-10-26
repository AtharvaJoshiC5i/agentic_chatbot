"""List and update recovery tasks."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import ActorType, SourceType, TaskStatus
from app.models.tables import RecoveryTask
from app.security.deps import CurrentUser
from app.services.audit import record_audit
from app.services.return_events import record_return_event


class RecoveryTaskServiceError(Exception):
    def __init__(self, message: str, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code


def list_recovery_tasks(
    session: Session,
    *,
    status: str | None = None,
    assigned_to: str | None = None,
    return_id: str | None = None,
    limit: int = 100,
) -> list[RecoveryTask]:
    query = select(RecoveryTask).order_by(RecoveryTask.recovery_task_id.desc())
    if status:
        query = query.where(RecoveryTask.task_status == status.strip().lower())
    if assigned_to:
        query = query.where(RecoveryTask.assigned_to == assigned_to.strip())
    if return_id:
        query = query.where(RecoveryTask.return_id == return_id.strip().upper())
    return list(session.execute(query.limit(limit)).scalars().all())


def update_recovery_task(
    session: Session,
    task_id: int,
    *,
    assigned_to: str | None = None,
    task_status: TaskStatus | None = None,
    actor: CurrentUser,
) -> RecoveryTask:
    task = session.get(RecoveryTask, task_id)
    if task is None:
        raise RecoveryTaskServiceError("Task not found", "not_found")

    if assigned_to is not None:
        task.assigned_to = assigned_to or None
        if assigned_to and task.task_status == TaskStatus.PENDING.value:
            task.task_status = TaskStatus.ASSIGNED.value

    if task_status is not None:
        task.task_status = task_status.value
        if task_status == TaskStatus.COMPLETED:
            task.completed_at = utc_now()

    record_return_event(
        session,
        return_id=task.return_id,
        event_type="other",
        description=f"Recovery task {task_id} updated to {task.task_status}.",
        source_type=SourceType.RECOVERY_TASK.value,
        source_id=str(task_id),
    )
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="update_recovery_task",
        target_entity="recovery_task",
        target_id=str(task_id),
        execution_result="succeeded",
        evidence_references={"task_status": task.task_status},
    )
    session.commit()
    session.refresh(task)
    return task
