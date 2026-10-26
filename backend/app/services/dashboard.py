"""Dashboard aggregate queries."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import (
    AlertStatus,
    CaseStatus,
    ReturnStatus,
    TaskStatus,
)
from app.models.tables import (
    InvestigationCase,
    RecoveryOption,
    RecoveryTask,
    Return,
    SystemAlert,
)
from app.services.actions import count_pending_actions
from app.services.refunds import count_refunds_pending_approval


def get_dashboard_summary(session: Session) -> dict:
    now = utc_now()
    total_returns = session.execute(select(func.count()).select_from(Return)).scalar_one()
    pending_investigations = session.execute(
        select(func.count())
        .select_from(InvestigationCase)
        .where(InvestigationCase.case_status.in_([CaseStatus.OPEN, CaseStatus.IN_PROGRESS, CaseStatus.ASSIGNED]))
    ).scalar_one()
    refunds_pending = count_refunds_pending_approval(session)
    actions_pending = count_pending_actions(session)
    open_recovery_tasks = session.execute(
        select(func.count())
        .select_from(RecoveryTask)
        .where(RecoveryTask.task_status.in_([TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]))
    ).scalar_one()
    estimated_recovery_value = session.execute(
        select(func.coalesce(func.sum(RecoveryOption.expected_net_recovery), 0))
    ).scalar_one()
    completed_recovery_tasks = session.execute(
        select(func.count())
        .select_from(RecoveryTask)
        .where(RecoveryTask.task_status == TaskStatus.COMPLETED)
    ).scalar_one()
    investigating_returns = session.execute(
        select(func.count()).select_from(Return).where(Return.return_status == ReturnStatus.INVESTIGATING)
    ).scalar_one()
    overdue_cases = session.execute(
        select(func.count())
        .select_from(InvestigationCase)
        .where(
            InvestigationCase.due_date.is_not(None),
            InvestigationCase.due_date < now,
            InvestigationCase.case_status.not_in([CaseStatus.RESOLVED, CaseStatus.CLOSED]),
        )
    ).scalar_one()
    open_system_alerts = session.execute(
        select(func.count())
        .select_from(SystemAlert)
        .where(SystemAlert.status == AlertStatus.OPEN.value)
    ).scalar_one()

    return {
        "total_returns": total_returns,
        "pending_investigations": pending_investigations,
        "refunds_awaiting_approval": refunds_pending,
        "actions_awaiting_approval": actions_pending,
        "open_recovery_tasks": open_recovery_tasks,
        "estimated_recovery_value_paise": int(estimated_recovery_value),
        "completed_recovery_tasks": completed_recovery_tasks,
        "returns_investigating": investigating_returns,
        "overdue_investigation_cases": overdue_cases,
        "open_system_alerts": int(open_system_alerts),
        "generated_at": now,
    }
